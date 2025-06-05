import win32serviceutil, win32service, win32event, servicemanager, subprocess, sys, os, signal
import time
import logging
from logging.handlers import RotatingFileHandler

# Configure paths - adjust these based on your project structure
EXE = sys.executable
APP = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")
PROFILE = os.getenv("SWARM_GPU_PROFILE", "rtx4070")   # fallback

class Agent0Service(win32serviceutil.ServiceFramework):
    _svc_name_ = "Agent0Council"
    _svc_display_name_ = "Agent-0 AutoGen Council"
    _svc_description_ = "Starts Agent-0 LLM swarm at boot and monitors health."
    _svc_deps_ = ["Winmgmt", "W32Time"]  # Dependencies: WMI and time service

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.proc = None
        self.running = False
        
        # Set up logging with rotation
        self.setup_logging()
        
        # Load environment variables from .env files
        self.load_environment()

    def load_environment(self):
        """Load environment variables from .env files"""
        try:
            from dotenv import load_dotenv
            
            # Load from .env.swarm if it exists
            env_file = os.path.join(os.path.dirname(__file__), "..", ".env.swarm")
            if os.path.exists(env_file):
                load_dotenv(env_file)
                self.logger.info(f"Loaded environment from {env_file}")
            
            # Also try .env
            env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
            if os.path.exists(env_file):
                load_dotenv(env_file)
                self.logger.info(f"Loaded environment from {env_file}")
                
        except ImportError:
            self.logger.warning("python-dotenv not available, skipping .env loading")
        except Exception as e:
            self.logger.error(f"Failed to load environment: {e}")

    def setup_logging(self):
        """Configure service logging with rotation to prevent bloat"""
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure rotating file handler - 20MB max, 5 backup files
        handler = RotatingFileHandler(
            os.path.join(log_dir, "agent0_service.log"),
            maxBytes=20*1024*1024,  # 20MB max file size
            backupCount=5
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        self.logger = logging.getLogger("Agent0Service")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def prefetch_models(self):
        """Pre-fetch models if needed"""
        try:
            work_dir = os.path.join(os.path.dirname(__file__), "..")
            prefetch_script = os.path.join(work_dir, "models", "prefetch.py")
            
            if os.path.exists(prefetch_script):
                self.logger.info("Running model prefetch...")
                result = subprocess.run(
                    [EXE, prefetch_script],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    self.logger.info("Model prefetch completed successfully")
                else:
                    self.logger.warning(f"Model prefetch returned code {result.returncode}: {result.stderr}")
            else:
                self.logger.info("No prefetch script found, skipping")
                
        except Exception as e:
            self.logger.error(f"Model prefetch failed: {e}")

    def SvcDoRun(self):
        """Main service loop"""
        self.running = True
        servicemanager.LogInfoMsg("Agent-0 starting …")
        self.logger.info("Agent-0 service starting")
        
        try:
            # Pre-fetch models on first run
            self.prefetch_models()
            
            # Start the Agent-0 application
            self.start_agent0()
            
            # Monitor loop
            while self.running:
                # Check if stop event is signaled
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
                
                # Check if process crashed
                if self.proc and self.proc.poll() is not None:
                    servicemanager.LogErrorMsg("Agent-0 crashed, restarting")
                    self.logger.error("Agent-0 process crashed, restarting")
                    time.sleep(5)  # Brief delay before restart
                    self.start_agent0()
                    
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            servicemanager.LogErrorMsg(f"Service error: {e}")
        
        servicemanager.LogInfoMsg("Agent-0 stopping …")
        self.logger.info("Agent-0 service stopping")

    def start_agent0(self):
        """Start the Agent-0 application process"""
        try:
            # Ensure we're in the correct working directory
            work_dir = os.path.join(os.path.dirname(__file__), "..")
            
            # Start the FastAPI application using uvicorn
            cmd = [
                EXE, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000",
                "--log-level", "info"
            ]
            
            # Set environment variables including GPU allocator fix
            env = os.environ.copy()
            env["SWARM_GPU_PROFILE"] = PROFILE
            env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
            env["AGENT0_SERVICE_MANAGED"] = "true"
            
            self.proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW  # Run without console window
            )
            
            self.logger.info(f"Started Agent-0 process with PID {self.proc.pid}")
            servicemanager.LogInfoMsg(f"Agent-0 started with PID {self.proc.pid}")
            
        except Exception as e:
            self.logger.error(f"Failed to start Agent-0: {e}")
            servicemanager.LogErrorMsg(f"Failed to start Agent-0: {e}")
            raise

    def SvcStop(self):
        """Stop the service"""
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        if self.proc and self.proc.poll() is None:
            try:
                # Try graceful shutdown first
                self.proc.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    self.proc.kill()
                    self.proc.wait()
                    
                self.logger.info("Agent-0 process stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Agent-0: {e}")
        
        win32event.SetEvent(self.hWaitStop)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(Agent0Service)
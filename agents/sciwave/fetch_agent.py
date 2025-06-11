#!/usr/bin/env python3
"""
SCI-100: Fetch Agent - ArXiv + PubMed Daily Scraper
📥 Autonomous research paper intake with success metrics

KPI Gate: arxiv_pull_success_total ≥ 3
Effort: 0.5 days
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote
import re
import time

logger = logging.getLogger(__name__)

@dataclass
class PaperMetadata:
    """Structured paper metadata"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    url: str
    published: datetime
    source: str  # 'arxiv' or 'pubmed'
    categories: List[str]
    doi: Optional[str] = None
    journal: Optional[str] = None

class FetchAgent:
    """SCI-100: ArXiv + PubMed daily scraper with metric tracking"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.arxiv_base_url = "http://export.arxiv.org/api/query"
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        # KPI tracking
        self.metrics = {
            'arxiv_pull_success_total': 0,
            'pubmed_pull_success_total': 0,
            'papers_fetched_today': 0,
            'fetch_failures': 0,
            'last_successful_run': None
        }
        
        # Default search queries
        self.default_queries = {
            'arxiv': [
                'cat:cs.AI OR cat:cs.CL OR cat:cs.LG',  # AI/ML/NLP
                'cat:stat.ML',  # Machine Learning Stats
                'cat:cs.CV'     # Computer Vision
            ],
            'pubmed': [
                'artificial intelligence[MeSH Terms]',
                'machine learning[Title/Abstract]',
                'natural language processing[Title/Abstract]'
            ]
        }
        
    async def fetch_arxiv_papers(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Fetch papers from ArXiv API"""
        try:
            # Calculate date range (last 7 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Build ArXiv query with date filtering
            date_filter = f"submittedDate:[{start_date.strftime('%Y%m%d')}* TO {end_date.strftime('%Y%m%d')}*]"
            full_query = f"({query}) AND {date_filter}"
            
            params = {
                'search_query': full_query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.arxiv_base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"ArXiv API error: {response.status}")
                        return []
                    
                    xml_content = await response.text()
                    
            # Parse XML response
            root = ET.fromstring(xml_content)
            papers = []
            
            # ArXiv namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    # Extract metadata
                    arxiv_id = entry.find('atom:id', ns).text.split('/')[-1]
                    title = entry.find('atom:title', ns).text.strip()
                    abstract = entry.find('atom:summary', ns).text.strip()
                    
                    # Authors
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name = author.find('atom:name', ns).text
                        authors.append(name)
                    
                    # Published date
                    published_str = entry.find('atom:published', ns).text
                    published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    
                    # Categories
                    categories = []
                    for category in entry.findall('atom:category', ns):
                        categories.append(category.get('term'))
                    
                    # URL
                    url = entry.find('atom:id', ns).text
                    
                    paper = PaperMetadata(
                        id=arxiv_id,
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=url,
                        published=published,
                        source='arxiv',
                        categories=categories
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse ArXiv entry: {e}")
                    continue
            
            logger.info(f"Fetched {len(papers)} papers from ArXiv")
            return papers
            
        except Exception as e:
            logger.error(f"ArXiv fetch failed: {e}")
            self.metrics['fetch_failures'] += 1
            return []

    async def fetch_pubmed_papers(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Fetch papers from PubMed API"""
        try:
            # First, search for PMIDs
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'sort': 'pub+date',
                'reldate': 7,  # Last 7 days
                'retmode': 'json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Search step
                search_url = f"{self.pubmed_base_url}/esearch.fcgi"
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        logger.error(f"PubMed search error: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    
                pmids = search_data.get('esearchresult', {}).get('idlist', [])
                if not pmids:
                    logger.info("No recent PubMed papers found")
                    return []
                
                # Fetch details
                fetch_params = {
                    'db': 'pubmed',
                    'id': ','.join(pmids),
                    'retmode': 'xml'
                }
                
                fetch_url = f"{self.pubmed_base_url}/efetch.fcgi"
                async with session.get(fetch_url, params=fetch_params) as response:
                    if response.status != 200:
                        logger.error(f"PubMed fetch error: {response.status}")
                        return []
                    
                    xml_content = await response.text()
            
            # Parse XML response
            root = ET.fromstring(xml_content)
            papers = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    # Extract metadata
                    pmid = article.find('.//PMID').text
                    title_elem = article.find('.//ArticleTitle')
                    title = title_elem.text if title_elem is not None else "No title"
                    
                    abstract_elem = article.find('.//Abstract/AbstractText')
                    abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
                    
                    # Authors
                    authors = []
                    for author in article.findall('.//Author'):
                        last_name = author.find('LastName')
                        first_name = author.find('ForeName')
                        if last_name is not None and first_name is not None:
                            authors.append(f"{first_name.text} {last_name.text}")
                    
                    # Publication date
                    pub_date = article.find('.//PubDate')
                    year = pub_date.find('Year').text if pub_date.find('Year') is not None else "2024"
                    month = pub_date.find('Month').text if pub_date.find('Month') is not None else "01"
                    day = pub_date.find('Day').text if pub_date.find('Day') is not None else "01"
                    
                    try:
                        published = datetime(int(year), int(month) if month.isdigit() else 1, int(day) if day.isdigit() else 1)
                    except:
                        published = datetime.now()
                    
                    # Journal
                    journal_elem = article.find('.//Journal/Title')
                    journal = journal_elem.text if journal_elem is not None else None
                    
                    # DOI
                    doi_elem = article.find('.//ELocationID[@EIdType="doi"]')
                    doi = doi_elem.text if doi_elem is not None else None
                    
                    paper = PaperMetadata(
                        id=pmid,
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        published=published,
                        source='pubmed',
                        categories=[],
                        doi=doi,
                        journal=journal
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse PubMed entry: {e}")
                    continue
            
            logger.info(f"Fetched {len(papers)} papers from PubMed")
            return papers
            
        except Exception as e:
            logger.error(f"PubMed fetch failed: {e}")
            self.metrics['fetch_failures'] += 1
            return []

    async def daily_fetch_cycle(self) -> Dict[str, Any]:
        """Execute daily paper fetching cycle with KPI tracking"""
        start_time = time.time()
        total_papers = []
        
        logger.info("Starting daily fetch cycle...")
        
        # Fetch from ArXiv
        for query in self.default_queries['arxiv']:
            papers = await self.fetch_arxiv_papers(query, max_results=5)
            total_papers.extend(papers)
            if papers:
                self.metrics['arxiv_pull_success_total'] += 1
        
        # Fetch from PubMed  
        for query in self.default_queries['pubmed']:
            papers = await self.fetch_pubmed_papers(query, max_results=5)
            total_papers.extend(papers)
            if papers:
                self.metrics['pubmed_pull_success_total'] += 1
        
        # Update metrics
        self.metrics['papers_fetched_today'] = len(total_papers)
        self.metrics['last_successful_run'] = datetime.now().isoformat()
        
        # Check KPI gate
        kpi_passed = self.metrics['arxiv_pull_success_total'] >= 3
        
        execution_time = time.time() - start_time
        
        result = {
            'papers': [paper.__dict__ for paper in total_papers],
            'metrics': self.metrics.copy(),
            'kpi_gate_passed': kpi_passed,
            'execution_time_seconds': execution_time,
            'status': 'success' if kpi_passed else 'kpi_failure',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Daily fetch completed: {len(total_papers)} papers, KPI: {kpi_passed}")
        
        return result

    async def search_papers(self, topic: str, sources: List[str] = None) -> List[PaperMetadata]:
        """Search for papers on a specific topic"""
        if sources is None:
            sources = ['arxiv', 'pubmed']
        
        papers = []
        
        if 'arxiv' in sources:
            # Convert topic to ArXiv query format
            arxiv_query = f"all:{topic}"
            arxiv_papers = await self.fetch_arxiv_papers(arxiv_query, max_results=10)
            papers.extend(arxiv_papers)
        
        if 'pubmed' in sources:
            # Use topic directly for PubMed
            pubmed_papers = await self.fetch_pubmed_papers(topic, max_results=10)
            papers.extend(pubmed_papers)
        
        return papers

    def get_metrics(self) -> Dict[str, Any]:
        """Get current fetch metrics"""
        return self.metrics.copy()

    def reset_metrics(self):
        """Reset daily metrics (for testing)"""
        self.metrics.update({
            'arxiv_pull_success_total': 0,
            'pubmed_pull_success_total': 0,
            'papers_fetched_today': 0,
            'fetch_failures': 0
        })

# Test function
async def test_fetch_agent():
    """Test the fetch agent functionality"""
    agent = FetchAgent()
    
    print("🔬 Testing SCI-100 Fetch Agent...")
    
    # Test daily cycle
    result = await agent.daily_fetch_cycle()
    
    print(f"Papers fetched: {len(result['papers'])}")
    print(f"KPI gate passed: {result['kpi_gate_passed']}")
    print(f"Execution time: {result['execution_time_seconds']:.2f}s")
    print(f"Metrics: {result['metrics']}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_fetch_agent()) 
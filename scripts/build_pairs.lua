-- scripts/build_pairs.lua
-- Redis Lua script to extract feedback and build preference pairs

local function build_preference_pairs()
    local pairs = {}
    
    -- Get all feedback keys
    local feedback_keys = redis.call('KEYS', 'feedback:*')
    
    for _, key in ipairs(feedback_keys) do
        -- Get all feedback data with scores
        local feedback_data = redis.call('ZRANGE', key, 0, -1, 'WITHSCORES')
        
        -- Group responses by prompt
        local prompt_responses = {}
        
        for i = 1, #feedback_data, 2 do
            local response_json = feedback_data[i]
            local score = tonumber(feedback_data[i + 1])
            
            -- Parse JSON (simple parsing for key extraction)
            local prompt_start = string.find(response_json, '"prompt":%s*"')
            local response_start = string.find(response_json, '"response":%s*"')
            
            if prompt_start and response_start then
                local prompt_end = string.find(response_json, '"', prompt_start + 10)
                local response_end = string.find(response_json, '"', response_start + 12)
                
                if prompt_end and response_end then
                    local prompt = string.sub(response_json, prompt_start + 10, prompt_end - 1)
                    local response = string.sub(response_json, response_start + 12, response_end - 1)
                    
                    if not prompt_responses[prompt] then
                        prompt_responses[prompt] = {}
                    end
                    
                    table.insert(prompt_responses[prompt], {
                        choice = response,
                        score = score
                    })
                end
            end
        end
        
        -- Create preference pairs
        for prompt, responses in pairs(prompt_responses) do
            if #responses >= 2 then
                -- Sort by score (descending)
                table.sort(responses, function(a, b) return a.score > b.score end)
                
                -- Create pairs from high vs low scoring responses
                for i = 1, #responses - 1 do
                    for j = i + 1, #responses do
                        local high_score = responses[i]
                        local low_score = responses[j]
                        
                        -- Only create pair if score difference is meaningful
                        if high_score.score - low_score.score > 0.1 then
                            -- High choice preferred (label 0)
                            local pair1 = string.format(
                                '{"prompt":"%s","choice_a":"%s","choice_b":"%s","label":0}',
                                prompt, high_score.choice, low_score.choice
                            )
                            table.insert(pairs, pair1)
                            
                            -- Reverse for balance (label 1)
                            local pair2 = string.format(
                                '{"prompt":"%s","choice_a":"%s","choice_b":"%s","label":1}',
                                prompt, low_score.choice, high_score.choice
                            )
                            table.insert(pairs, pair2)
                        end
                    end
                end
            end
        end
    end
    
    return pairs
end

-- Main execution
local pairs = build_preference_pairs()

-- Write to Redis list for processing
if #pairs > 0 then
    redis.call('DEL', 'preference_pairs_staging')
    for _, pair in ipairs(pairs) do
        redis.call('LPUSH', 'preference_pairs_staging', pair)
    end
    redis.call('EXPIRE', 'preference_pairs_staging', 3600)  -- 1 hour TTL
end

return #pairs 
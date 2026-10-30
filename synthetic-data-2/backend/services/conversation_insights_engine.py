"""
Real-Time Marketing Insights Dashboard
Generates actionable metrics from persona group conversations
"""

from typing import List, Dict, Any
import json
from datetime import datetime
import boto3
from collections import Counter


class ConversationInsightsEngine:
    """
    Analyzes group chat conversations to generate real marketing metrics
    """
    
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    async def generate_insights_dashboard(
        self,
        conversation_history: List[Dict],
        personas: List[Dict],
        product_context: str,
        campaign_goal: str
    ) -> Dict[str, Any]:
        """
        Generate real-time marketing insights from group conversation
        
        Args:
            conversation_history: List of messages in group chat
            personas: List of persona objects with traits
            product_context: What product/campaign is being discussed
            campaign_goal: Campaign objective (awareness, sales, etc.)
        
        Returns:
            Dashboard data with actionable metrics
        """
        
        # Step 1: Extract persona responses from conversation
        persona_responses = self._extract_persona_responses(conversation_history)
        
        # Step 2: Call LLM to analyze responses and generate metrics
        analysis_prompt = self._build_analysis_prompt(
            persona_responses, 
            personas, 
            product_context,
            campaign_goal
        )
        
        llm_analysis = await self._call_llm_for_analysis(analysis_prompt)
        
        # Step 3: Calculate demographic distributions
        demographic_distribution = self._calculate_demographic_distribution(personas)
        
        # Step 4: Combine into dashboard
        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "campaign_context": product_context,
            "total_personas_analyzed": len(personas),
            "conversation_messages": len(conversation_history),
            
            # Real actionable metrics
            "key_metrics": llm_analysis.get("key_metrics", {}),
            "demographic_distribution": demographic_distribution,
            "sentiment_breakdown": llm_analysis.get("sentiment_breakdown", {}),
            "purchase_funnel": llm_analysis.get("purchase_funnel", {}),
            "objections_analysis": llm_analysis.get("objections", []),
            "recommendations": llm_analysis.get("recommendations", []),
            
            # Visualizations data
            "charts": {
                "add_to_cart_rate": self._format_gauge_data(
                    llm_analysis.get("key_metrics", {}).get("add_to_cart_rate", 0)
                ),
                "purchase_intent_distribution": self._format_pie_data(
                    llm_analysis.get("purchase_funnel", {})
                ),
                "demographic_performance": self._format_bar_data(
                    llm_analysis.get("demographic_performance", {})
                ),
                "sentiment_gauge": self._format_sentiment_gauge(
                    llm_analysis.get("sentiment_breakdown", {})
                )
            }
        }
        
        return dashboard
    
    def _extract_persona_responses(self, conversation_history: List[Dict]) -> List[Dict]:
        """Extract only persona responses (not user messages)"""
        persona_responses = []
        for message in conversation_history:
            if message.get("role") == "assistant":
                persona_responses.append({
                    "persona_id": message.get("persona_id"),
                    "response": message.get("content"),
                    "timestamp": message.get("timestamp")
                })
        return persona_responses
    
    def _build_analysis_prompt(
        self, 
        persona_responses: List[Dict],
        personas: List[Dict],
        product_context: str,
        campaign_goal: str
    ) -> str:
        """Build LLM prompt for real-time metric analysis"""
        
        # Format persona responses for LLM
        responses_text = "\n\n".join([
            f"Persona {i+1} ({p.get('segment_name', 'Unknown')}): {p['response']}"
            for i, p in enumerate(persona_responses)
        ])
        
        # Format persona demographics
        demographics_summary = self._summarize_demographics(personas)
        
        prompt = f"""
You are a marketing analytics AI analyzing real customer feedback from a focus group.

## Campaign Context:
Product/Campaign: {product_context}
Campaign Goal: {campaign_goal}
Number of Participants: {len(personas)}

## Participant Demographics:
{demographics_summary}

## Focus Group Responses:
{responses_text}

## Your Task:
Analyze these responses and generate ACTIONABLE MARKETING METRICS. Output must be in JSON format.

## Required Metrics (JSON Schema):

{{
  "key_metrics": {{
    "add_to_cart_rate": 0-100,  // % of personas likely to add product to cart
    "purchase_intent_score": 0-100,  // Overall purchase likelihood
    "brand_affinity": 0-100,  // How much they like the brand
    "message_clarity": 0-100,  // How well they understood the value prop
    "price_sensitivity": "low" | "medium" | "high",  // Price concerns
    "recommendation_likelihood": 0-100  // Net Promoter Score equivalent
  }},
  
  "sentiment_breakdown": {{
    "positive": 0-100,  // % positive sentiment
    "neutral": 0-100,
    "negative": 0-100,
    "overall_sentiment": "positive" | "neutral" | "negative"
  }},
  
  "purchase_funnel": {{
    "awareness": 0-100,  // Already aware of product/brand
    "consideration": 0-100,  // Considering purchase
    "intent": 0-100,  // Strong intent to buy
    "action": 0-100  // Would buy immediately
  }},
  
  "demographic_performance": {{
    "age_18_24": {{"engagement": 0-100, "conversion_potential": 0-100}},
    "age_25_34": {{"engagement": 0-100, "conversion_potential": 0-100}},
    "age_35_44": {{"engagement": 0-100, "conversion_potential": 0-100}},
    "age_45_plus": {{"engagement": 0-100, "conversion_potential": 0-100}},
    "best_performing_segment": "segment_name"
  }},
  
  "objections": [
    {{
      "objection": "specific concern raised",
      "severity": "high" | "medium" | "low",
      "frequency": "how many personas mentioned it",
      "recommended_response": "how to address this objection"
    }}
  ],
  
  "key_themes": [
    {{
      "theme": "theme name",
      "sentiment": "positive" | "negative" | "neutral",
      "personas_mentioned": ["persona1", "persona2"],
      "impact": "high" | "medium" | "low"
    }}
  ],
  
  "recommendations": [
    {{
      "priority": "high" | "medium" | "low",
      "action": "specific actionable recommendation",
      "expected_impact": "what this will improve",
      "target_segment": "which audience to focus on"
    }}
  ],
  
  "targeting_insights": {{
    "primary_audience": "best segment to target",
    "secondary_audience": "backup segment",
    "avoid_segments": ["segments unlikely to convert"],
    "recommended_channels": ["channel1", "channel2"],
    "optimal_messaging": "key message that resonated most"
  }}
}}

## Analysis Rules:
1. Base metrics ONLY on actual responses (no guessing)
2. Be specific - cite which personas had which reactions
3. Calculate add_to_cart_rate based on explicit purchase interest
4. Identify ACTIONABLE insights (not generic observations)
5. Flag any red flags (negative sentiment, confusion, objections)
6. Recommend specific targeting/messaging changes

Generate the complete JSON analysis now.
"""
        return prompt
    
    async def _call_llm_for_analysis(self, prompt: str) -> Dict[str, Any]:
        """Call Claude to analyze conversation and return metrics"""
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,  # Lower for more consistent metrics
                    "top_p": 0.9
                })
            )
            
            response_body = json.loads(response['body'].read())
            analysis_text = response_body['content'][0]['text']
            
            # Parse JSON from response
            # Claude might wrap JSON in markdown, so extract it
            if "```json" in analysis_text:
                json_start = analysis_text.find("```json") + 7
                json_end = analysis_text.find("```", json_start)
                analysis_text = analysis_text[json_start:json_end].strip()
            
            analysis = json.loads(analysis_text)
            return analysis
            
        except Exception as e:
            print(f"Error calling LLM for analysis: {e}")
            # Return fallback structure
            return {
                "key_metrics": {
                    "add_to_cart_rate": 0,
                    "purchase_intent_score": 0,
                    "brand_affinity": 0
                },
                "sentiment_breakdown": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                },
                "recommendations": []
            }
    
    def _calculate_demographic_distribution(self, personas: List[Dict]) -> Dict[str, Any]:
        """Calculate real demographic breakdown"""
        
        age_groups = Counter()
        genders = Counter()
        locations = Counter()
        
        for persona in personas:
            demo = persona.get("demographic_info", {})
            
            # Age grouping
            age = demo.get("age", 30)
            if age < 25:
                age_groups["18-24"] += 1
            elif age < 35:
                age_groups["25-34"] += 1
            elif age < 45:
                age_groups["35-44"] += 1
            else:
                age_groups["45+"] += 1
            
            # Gender
            gender = demo.get("gender", "unknown")
            genders[gender] += 1
            
            # Location (if available)
            location = demo.get("location", {}).get("city", "Unknown")
            locations[location] += 1
        
        total = len(personas)
        
        return {
            "age_distribution": {k: round((v/total)*100, 1) for k, v in age_groups.items()},
            "gender_distribution": {k: round((v/total)*100, 1) for k, v in genders.items()},
            "top_locations": dict(locations.most_common(5))
        }
    
    def _summarize_demographics(self, personas: List[Dict]) -> str:
        """Create human-readable demographic summary"""
        age_counts = Counter()
        gender_counts = Counter()
        
        for persona in personas:
            demo = persona.get("demographic_info", {})
            age = demo.get("age", 30)
            if age < 25:
                age_counts["18-24"] += 1
            elif age < 35:
                age_counts["25-34"] += 1
            elif age < 45:
                age_counts["35-44"] += 1
            else:
                age_counts["45+"] += 1
            
            gender_counts[demo.get("gender", "unknown")] += 1
        
        summary = "Age Groups: " + ", ".join([f"{k}: {v}" for k, v in age_counts.items()])
        summary += "\nGenders: " + ", ".join([f"{k}: {v}" for k, v in gender_counts.items()])
        return summary
    
    # Visualization formatters
    def _format_gauge_data(self, value: float) -> Dict:
        """Format data for gauge chart"""
        return {
            "type": "gauge",
            "value": value,
            "min": 0,
            "max": 100,
            "thresholds": [
                {"value": 30, "color": "red", "label": "Low"},
                {"value": 60, "color": "yellow", "label": "Medium"},
                {"value": 100, "color": "green", "label": "High"}
            ]
        }
    
    def _format_pie_data(self, funnel_data: Dict) -> Dict:
        """Format purchase funnel as pie chart"""
        return {
            "type": "pie",
            "data": [
                {"label": "Awareness", "value": funnel_data.get("awareness", 0)},
                {"label": "Consideration", "value": funnel_data.get("consideration", 0)},
                {"label": "Intent", "value": funnel_data.get("intent", 0)},
                {"label": "Ready to Buy", "value": funnel_data.get("action", 0)}
            ]
        }
    
    def _format_bar_data(self, demographic_perf: Dict) -> Dict:
        """Format demographic performance as bar chart"""
        bars = []
        for segment, data in demographic_perf.items():
            if segment != "best_performing_segment":
                bars.append({
                    "label": segment.replace("_", " ").title(),
                    "engagement": data.get("engagement", 0),
                    "conversion": data.get("conversion_potential", 0)
                })
        
        return {
            "type": "grouped_bar",
            "data": bars
        }
    
    def _format_sentiment_gauge(self, sentiment: Dict) -> Dict:
        """Format sentiment as gauge"""
        # Calculate net sentiment score
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)
        net_score = positive - negative
        
        
        return {
            "type": "sentiment_gauge",
            "net_score": net_score,
            "positive": positive,
            "neutral": sentiment.get("neutral", 0),
            "negative": negative,
            "overall": sentiment.get("overall_sentiment", "neutral")
        }
    
    async def generate_insights_with_persona_analysis(
        self,
        personas: List[Dict],
        product_context: str,
        campaign_goal: str,
        uploaded_assets: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Ask each persona to analyze the asset/product with structured template
        and aggregate responses into metrics
        """
        import asyncio
        
        print(f"🎯 Starting structured persona analysis for {len(personas)} personas...")
        
        # Step 1: Create structured analysis prompt for each persona
        async def analyze_persona(persona: Dict, index: int) -> Dict:
            """Ask one persona to analyze with structured template"""
            
            analysis_prompt = f"""You are analyzing a marketing campaign as this persona:

**Persona Profile:**
{persona.get('narrative_profile', 'Healthcare professional interested in skincare')}

**Product/Campaign:**
{product_context}

**Campaign Goal:**
{campaign_goal}

**Your Task:**
Please analyze this product/campaign from YOUR persona's perspective and provide your honest opinion.

**IMPORTANT: Respond ONLY with valid JSON in this exact format:**

{{
  "will_add_to_cart": true/false,
  "purchase_intent": 0-100,
  "brand_sentiment": "positive"/"neutral"/"negative",
  "would_recommend": true/false,
  "key_objection": "your main concern or 'none'",
  "what_appeals_most": "what you like most",
  "purchase_likelihood": "definitely"/"probably"/"maybe"/"unlikely"/"never",
  "price_sensitivity": "low"/"medium"/"high",
  "demographic_factor": "any demographic factor that influences your opinion"
}}

Think like your persona and respond with genuine reactions. Be honest - if something doesn't appeal to you, say so!
"""
            
            # Call Claude to get persona's structured response
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [{
                            "role": "user",
                            "content": analysis_prompt
                        }]
                    })
                )
                
                result = json.loads(response['body'].read())
                response_text = result['content'][0]['text']
                
                # Parse JSON from response
                # Clean up response (remove markdown code blocks if present)
                response_text = response_text.strip()
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                response_text = response_text.strip()
                
                persona_analysis = json.loads(response_text)
                persona_analysis['persona_index'] = index
                persona_analysis['persona_segment'] = persona.get('segment_name', 'Unknown')
                
                print(f"✅ Persona {index+1} analyzed - Purchase intent: {persona_analysis.get('purchase_intent', 0)}%")
                return persona_analysis
                
            except Exception as e:
                print(f"❌ Error analyzing persona {index+1}: {e}")
                # Return default neutral response
                return {
                    "will_add_to_cart": False,
                    "purchase_intent": 50,
                    "brand_sentiment": "neutral",
                    "would_recommend": False,
                    "key_objection": "Unable to analyze",
                    "what_appeals_most": "N/A",
                    "purchase_likelihood": "maybe",
                    "price_sensitivity": "medium",
                    "persona_index": index,
                    "persona_segment": persona.get('segment_name', 'Unknown')
                }
        
        # Step 2: Run all persona analyses in parallel
        tasks = [analyze_persona(persona, i) for i, persona in enumerate(personas)]
        persona_analyses = await asyncio.gather(*tasks)
        
        # Step 3: Aggregate responses into metrics
        metrics = self._aggregate_persona_analyses(persona_analyses, personas)
        
        print(f"📊 Aggregated metrics - Add to cart: {metrics['key_metrics']['add_to_cart_rate']}%")
        
        return metrics
    
    def _aggregate_persona_analyses(self, analyses: List[Dict], personas: List[Dict]) -> Dict[str, Any]:
        """Aggregate individual persona analyses into dashboard metrics"""
        
        total = len(analyses)
        if total == 0:
            total = 1  # Avoid division by zero
        
        # Calculate key metrics
        add_to_cart_count = sum(1 for a in analyses if a.get('will_add_to_cart', False))
        recommend_count = sum(1 for a in analyses if a.get('would_recommend', False))
        avg_purchase_intent = sum(a.get('purchase_intent', 0) for a in analyses) / total
        
        # Sentiment breakdown (FIXED: now percentages)
        sentiment_counts = Counter(a.get('brand_sentiment', 'neutral') for a in analyses)
        
        # Purchase funnel
        funnel_counts = Counter(a.get('purchase_likelihood', 'maybe') for a in analyses)
        
        # Price sensitivity analysis
        price_counts = Counter(a.get('price_sensitivity', 'medium') for a in analyses)
        
        # Objections - group similar ones
        objections = [a.get('key_objection') for a in analyses if a.get('key_objection') and a.get('key_objection') != 'none']
        objection_counts = Counter(objections)
        
        # Calculate appeal factors
        appeals = [a.get('what_appeals_most') for a in analyses if a.get('what_appeals_most')]
        appeal_counts = Counter(appeals)
        
        # Demographics
        demographic_distribution = self._calculate_demographic_distribution(personas)
        
        # NEW: Calculate conversion probability (definitely + probably)
        high_intent_count = funnel_counts.get('definitely', 0) + funnel_counts.get('probably', 0)
        conversion_probability = round((high_intent_count / total) * 100)
        
        # NEW: Calculate engagement score (based on detailed responses)
        engagement_score = round(((recommend_count + add_to_cart_count) / (total * 2)) * 100)
        
        # NEW: Risk assessment (negative sentiment + objections)
        risk_score = round(((sentiment_counts.get('negative', 0) + len(objections)) / (total * 2)) * 100)
        
        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "campaign_context": "Product analysis",
            "total_personas_analyzed": total,
            "conversation_messages": 0,
            
            "key_metrics": {
                "add_to_cart_rate": round((add_to_cart_count / total) * 100),
                "purchase_intent_score": round(avg_purchase_intent),
                "brand_affinity": round((sentiment_counts.get('positive', 0) / total) * 100),
                "net_promoter_score": round((recommend_count / total) * 100),
                # NEW METRICS
                "conversion_probability": conversion_probability,
                "engagement_score": engagement_score,
                "risk_score": risk_score,
                "market_readiness": "High" if conversion_probability >= 60 else ("Medium" if conversion_probability >= 30 else "Low")
            },
            
            "demographic_distribution": demographic_distribution,
            
            # FIXED: Now showing percentages
            "sentiment_breakdown": {
                "positive": round((sentiment_counts.get('positive', 0) / total) * 100),
                "neutral": round((sentiment_counts.get('neutral', 0) / total) * 100),
                "negative": round((sentiment_counts.get('negative', 0) / total) * 100)
            },
            
            # NEW: Price sensitivity breakdown
            "price_sensitivity": {
                "low": round((price_counts.get('low', 0) / total) * 100),
                "medium": round((price_counts.get('medium', 0) / total) * 100),
                "high": round((price_counts.get('high', 0) / total) * 100)
            },
            
            "purchase_funnel": {
                "definitely": round((funnel_counts.get('definitely', 0) / total) * 100),
                "probably": round((funnel_counts.get('probably', 0) / total) * 100),
                "maybe": round((funnel_counts.get('maybe', 0) / total) * 100),
                "unlikely": round((funnel_counts.get('unlikely', 0) / total) * 100),
                "never": round((funnel_counts.get('never', 0) / total) * 100)
            },
            
            # NEW: Top appeal factors
            "top_appeal_factors": [
                {"factor": appeal, "count": count, "percentage": round((count/total)*100)}
                for appeal, count in appeal_counts.most_common(3)
            ],
            
            "objections_analysis": [
                {"objection": obj, "count": count, "percentage": round((count/total)*100)}
                for obj, count in objection_counts.most_common(5)
            ],
            
            # NEW: Grouped objections by theme
            "objection_themes": self._group_objections_by_theme(objections, total),
            
            "recommendations": self._generate_recommendations(analyses, total),
            
            "charts": {
                "add_to_cart_rate": self._format_gauge_data(round((add_to_cart_count / total) * 100)),
                "purchase_intent_distribution": {
                    "type": "pie",
                    "data": [
                        {"label": k.title(), "value": round((v/total)*100)} 
                        for k, v in funnel_counts.items()
                    ]
                },
                "demographic_performance": self._format_bar_data({}),
                "sentiment_gauge": {
                    "type": "sentiment_gauge",
                    "net_score": sentiment_counts.get('positive', 0) - sentiment_counts.get('negative', 0),
                    "positive": round((sentiment_counts.get('positive', 0) / total) * 100),
                    "neutral": round((sentiment_counts.get('neutral', 0) / total) * 100),
                    "negative": round((sentiment_counts.get('negative', 0) / total) * 100),
                    "overall": max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "neutral"
                },
                # NEW: Price sensitivity chart
                "price_sensitivity_chart": {
                    "type": "bar",
                    "data": [
                        {"label": "Low", "value": round((price_counts.get('low', 0) / total) * 100)},
                        {"label": "Medium", "value": round((price_counts.get('medium', 0) / total) * 100)},
                        {"label": "High", "value": round((price_counts.get('high', 0) / total) * 100)}
                    ]
                }
            },
            
            "raw_analyses": analyses  # Include raw data for debugging
        }
        
        return dashboard
    
    def _group_objections_by_theme(self, objections: List[str], total: int) -> List[Dict]:
        """Group similar objections into themes"""
        themes = {
            "Clinical Evidence": [],
            "Ingredient Concerns": [],
            "Price/Value": [],
            "Product Format": [],
            "Other": []
        }
        
        for obj in objections:
            obj_lower = obj.lower()
            if any(word in obj_lower for word in ['clinical', 'studies', 'evidence', 'research', 'data']):
                themes["Clinical Evidence"].append(obj)
            elif any(word in obj_lower for word in ['ingredient', 'concentration', 'formulation', 'stability']):
                themes["Ingredient Concerns"].append(obj)
            elif any(word in obj_lower for word in ['price', 'cost', 'expensive', 'budget']):
                themes["Price/Value"].append(obj)
            elif any(word in obj_lower for word in ['packaging', 'format', 'application']):
                themes["Product Format"].append(obj)
            else:
                themes["Other"].append(obj)
        
        return [
            {
                "theme": theme,
                "count": len(objs),
                "percentage": round((len(objs)/total)*100) if objs else 0,
                "examples": objs[:2]  # Show top 2 examples
            }
            for theme, objs in themes.items()
            if objs  # Only include themes with objections
        ]
    
    def _generate_recommendations(self, analyses: List[Dict], total: int) -> List[Dict]:
        """Generate targeting recommendations based on analyses"""
        recommendations = []
        
        # Find most common appeal
        appeals = [a.get('what_appeals_most') for a in analyses if a.get('what_appeals_most')]
        if appeals:
            appeal_counts = Counter(appeals)
            top_appeal = appeal_counts.most_common(1)[0]
            appeal_pct = round((top_appeal[1]/total)*100)
            recommendations.append({
                "priority": "High",
                "action": f"Lead with: '{top_appeal[0][:60]}...'",
                "expected_impact": f"Resonates with {appeal_pct}% of audience - use as primary messaging",
                "percentage": appeal_pct
            })
        
        # Check price sensitivity
        price_sensitive = sum(1 for a in analyses if a.get('price_sensitivity') == 'high')
        if price_sensitive > total / 2:
            price_pct = round((price_sensitive/total)*100)
            recommendations.append({
                "priority": "High",
                "action": "Implement pricing strategy or payment plans",
                "expected_impact": f"{price_pct}% are price-sensitive - discounts/financing could increase conversion",
                "percentage": price_pct
            })
        
        # Analyze objections for clinical evidence
        objections = [a.get('key_objection') for a in analyses if a.get('key_objection') and a.get('key_objection') != 'none']
        if objections:
            # Check for common themes in objections
            if any('clinical' in obj.lower() or 'evidence' in obj.lower() or 'studies' in obj.lower() for obj in objections):
                clinical_count = sum(1 for obj in objections if 'clinical' in obj.lower() or 'evidence' in obj.lower() or 'studies' in obj.lower())
                clinical_pct = round((clinical_count/total)*100)
                recommendations.append({
                    "priority": "Critical",
                    "action": "Add clinical study references and peer-reviewed data",
                    "expected_impact": f"{clinical_pct}% need scientific validation - could increase trust by 25-40%",
                    "percentage": clinical_pct
                })
            
            if any('ingredient' in obj.lower() or 'concentration' in obj.lower() for obj in objections):
                ingredient_count = sum(1 for obj in objections if 'ingredient' in obj.lower() or 'concentration' in obj.lower())
                ingredient_pct = round((ingredient_count/total)*100)
                recommendations.append({
                    "priority": "High",
                    "action": "Highlight ingredient concentrations and sourcing",
                    "expected_impact": f"{ingredient_pct}% want transparency - detailed ingredient list could boost confidence",
                    "percentage": ingredient_pct
                })
        
        # Conversion readiness
        high_intent = sum(1 for a in analyses if a.get('purchase_likelihood') in ['definitely', 'probably'])
        if high_intent > total * 0.6:
            intent_pct = round((high_intent/total)*100)
            recommendations.append({
                "priority": "Medium",
                "action": "Create urgency with limited-time offers",
                "expected_impact": f"{intent_pct}% ready to buy now - urgency tactics could accelerate purchases",
                "percentage": intent_pct
            })
        
        # Recommender potential
        recommenders = sum(1 for a in analyses if a.get('would_recommend', False))
        if recommenders > total * 0.5:
            rec_pct = round((recommenders/total)*100)
            recommendations.append({
                "priority": "Medium",
                "action": "Launch referral/word-of-mouth program",
                "expected_impact": f"{rec_pct}% would recommend - referral program could expand reach organically",
                "percentage": rec_pct
            })
        
        return recommendations[:6]  # Top 6 actionable recommendations


"""
Marketing Dashboard Generator - Usage Examples
Demonstrates how to use the marketing dashboard template
"""

import json
from datetime import datetime
from templates.marketing_dashboard_template import (
    MARKETING_DASHBOARD_TEMPLATE,
    DASHBOARD_GENERATION_PROMPT,
    CHANNEL_SPECIFIC_PROMPTS,
    VISUALIZATION_CONFIG
)

# Example 1: Generate dashboard prompt for a beauty product campaign
def generate_beauty_campaign_dashboard_prompt():
    """
    Example: Beauty product launch campaign
    """
    campaign_data = {
        "campaign_name": "Luxury Skincare Spring Launch 2025",
        "campaign_objective": "Drive product awareness and online sales",
        "target_audience": "Women aged 25-45, interested in premium skincare",
        "start_date": "2025-03-01",
        "end_date": "2025-05-31",
        "total_budget": 150000,
        "industry": "Beauty & Cosmetics",
        "raw_data": {
            "impressions": 2500000,
            "reach": 850000,
            "clicks": 75000,
            "conversions": 2100,
            "revenue": 315000,
            "budget_spent": 142000,
            "video_views": 450000,
            "video_completion_rate": 62,
            "engagement_rate": 4.2,
            "leads": 3500,
            "demographics": {
                "age_25_34": 45,
                "age_35_44": 35,
                "age_45_plus": 20
            },
            "channels": {
                "instagram": {"impressions": 1200000, "clicks": 38000, "conversions": 950, "cost": 58000},
                "facebook": {"impressions": 800000, "clicks": 22000, "conversions": 650, "cost": 45000},
                "google_display": {"impressions": 500000, "clicks": 15000, "conversions": 500, "cost": 39000}
            },
            "top_creatives": [
                {"id": "creative_001", "type": "video", "ctr": 5.2, "conversions": 850},
                {"id": "creative_002", "type": "carousel", "ctr": 4.8, "conversions": 720},
                {"id": "creative_003", "type": "static_image", "ctr": 3.1, "conversions": 530}
            ]
        },
        "industry_benchmarks": {
            "beauty_ctr": 3.5,
            "beauty_conversion_rate": 2.8,
            "beauty_engagement_rate": 3.8,
            "beauty_roas": 2.5
        }
    }
    
    # Select relevant metric categories for this campaign
    selected_categories = [
        "Campaign Overview",
        "Engagement Metrics",
        "Conversion Metrics",
        "Audience Insights",
        "Channel Performance",
        "Content Performance",
        "Cost Efficiency",
        "Predictive Insights"
    ]
    
    # Generate the prompt
    prompt = DASHBOARD_GENERATION_PROMPT.format(
        campaign_name=campaign_data["campaign_name"],
        campaign_objective=campaign_data["campaign_objective"],
        target_audience=campaign_data["target_audience"],
        start_date=campaign_data["start_date"],
        end_date=campaign_data["end_date"],
        total_budget=campaign_data["total_budget"],
        industry=campaign_data["industry"],
        raw_data=json.dumps(campaign_data["raw_data"], indent=2),
        metric_categories=", ".join(selected_categories),
        industry_benchmarks=json.dumps(campaign_data["industry_benchmarks"], indent=2)
    )
    
    # Add social media specific analysis (primary channel)
    prompt += "\n\n" + CHANNEL_SPECIFIC_PROMPTS["social_media"]
    
    return prompt


# Example 2: Generate dashboard for e-commerce campaign
def generate_ecommerce_dashboard_prompt():
    """
    Example: E-commerce holiday sale campaign
    """
    campaign_data = {
        "campaign_name": "Black Friday Mega Sale 2025",
        "campaign_objective": "Maximize sales and clear inventory",
        "target_audience": "Bargain hunters, existing customers, 18-55",
        "start_date": "2025-11-20",
        "end_date": "2025-11-30",
        "total_budget": 250000,
        "industry": "E-commerce/Retail",
        "raw_data": {
            "impressions": 5500000,
            "reach": 1800000,
            "clicks": 185000,
            "conversions": 8500,
            "revenue": 1275000,
            "budget_spent": 238000,
            "cart_additions": 25000,
            "cart_abandonment_rate": 68,
            "average_order_value": 150,
            "repeat_customer_rate": 35,
            "channels": {
                "google_search": {"impressions": 2000000, "clicks": 95000, "conversions": 4200, "cost": 98000},
                "facebook": {"impressions": 1800000, "clicks": 52000, "conversions": 2400, "cost": 75000},
                "email": {"sent": 500000, "opens": 175000, "clicks": 38000, "conversions": 1900, "cost": 15000},
                "display": {"impressions": 1700000, "clicks": 12000, "conversions": 800, "cost": 50000}
            },
            "device_breakdown": {
                "mobile": 62,
                "desktop": 28,
                "tablet": 10
            },
            "time_analysis": {
                "peak_hour": "9 PM - 11 PM",
                "peak_day": "Black Friday (Nov 24)",
                "weekend_vs_weekday": "Weekend performed 32% better"
            }
        },
        "industry_benchmarks": {
            "ecommerce_ctr": 2.1,
            "ecommerce_conversion_rate": 3.5,
            "ecommerce_cart_abandonment": 70,
            "ecommerce_roas": 4.0
        }
    }
    
    selected_categories = [
        "Campaign Overview",
        "Engagement Metrics",
        "Conversion Metrics",
        "Audience Insights",
        "Channel Performance",
        "Time-Based Analysis",
        "Cost Efficiency",
        "Predictive Insights"
    ]
    
    prompt = DASHBOARD_GENERATION_PROMPT.format(
        campaign_name=campaign_data["campaign_name"],
        campaign_objective=campaign_data["campaign_objective"],
        target_audience=campaign_data["target_audience"],
        start_date=campaign_data["start_date"],
        end_date=campaign_data["end_date"],
        total_budget=campaign_data["total_budget"],
        industry=campaign_data["industry"],
        raw_data=json.dumps(campaign_data["raw_data"], indent=2),
        metric_categories=", ".join(selected_categories),
        industry_benchmarks=json.dumps(campaign_data["industry_benchmarks"], indent=2)
    )
    
    # Add paid search and email specific prompts
    prompt += "\n\n## Additional Channel Analysis:\n"
    prompt += CHANNEL_SPECIFIC_PROMPTS["paid_search"]
    prompt += "\n" + CHANNEL_SPECIFIC_PROMPTS["email_marketing"]
    
    return prompt


# Example 3: Generate dashboard for SaaS lead generation campaign
def generate_saas_leadgen_dashboard_prompt():
    """
    Example: SaaS B2B lead generation campaign
    """
    campaign_data = {
        "campaign_name": "Enterprise Software Q2 Lead Gen",
        "campaign_objective": "Generate qualified B2B leads for sales team",
        "target_audience": "CTOs, IT Directors at companies 100-1000 employees",
        "start_date": "2025-04-01",
        "end_date": "2025-06-30",
        "total_budget": 180000,
        "industry": "SaaS/B2B Software",
        "raw_data": {
            "impressions": 1200000,
            "reach": 450000,
            "clicks": 42000,
            "leads": 1250,
            "qualified_leads": 485,
            "sales_opportunities": 125,
            "closed_deals": 18,
            "revenue": 540000,
            "budget_spent": 175000,
            "content_downloads": 850,
            "webinar_registrations": 420,
            "demo_requests": 285,
            "channels": {
                "linkedin": {"impressions": 600000, "clicks": 22000, "leads": 680, "cost": 85000},
                "google_search": {"impressions": 400000, "clicks": 15000, "leads": 420, "cost": 65000},
                "content_marketing": {"impressions": 200000, "clicks": 5000, "leads": 150, "cost": 25000}
            },
            "lead_quality": {
                "marketing_qualified": 1250,
                "sales_qualified": 485,
                "qualification_rate": 38.8
            },
            "sales_cycle": {
                "average_days_to_close": 45,
                "lead_to_opportunity": 25.7,
                "opportunity_to_close": 14.4
            }
        },
        "industry_benchmarks": {
            "b2b_ctr": 2.0,
            "b2b_lead_qualification_rate": 35,
            "b2b_cpl": 140,
            "b2b_customer_acquisition_cost": 3000
        }
    }
    
    selected_categories = [
        "Campaign Overview",
        "Conversion Metrics",
        "Audience Insights",
        "Channel Performance",
        "Cost Efficiency",
        "Predictive Insights"
    ]
    
    prompt = DASHBOARD_GENERATION_PROMPT.format(
        campaign_name=campaign_data["campaign_name"],
        campaign_objective=campaign_data["campaign_objective"],
        target_audience=campaign_data["target_audience"],
        start_date=campaign_data["start_date"],
        end_date=campaign_data["end_date"],
        total_budget=campaign_data["total_budget"],
        industry=campaign_data["industry"],
        raw_data=json.dumps(campaign_data["raw_data"], indent=2),
        metric_categories=", ".join(selected_categories),
        industry_benchmarks=json.dumps(campaign_data["industry_benchmarks"], indent=2)
    )
    
    # Add B2B specific analysis
    prompt += """
    
    ## B2B Specific Analysis:
    - Lead qualification rate and quality
    - Sales cycle length and conversion stages
    - Customer acquisition cost (CAC) vs lifetime value (LTV)
    - MQL to SQL conversion rate
    - Demo-to-close ratio
    - Decision maker engagement
    - Account-based marketing (ABM) performance
    """
    
    return prompt


# Function to send prompt to LLM and generate dashboard
async def generate_dashboard_with_llm(campaign_data: dict, llm_client):
    """
    Use the template to generate a dashboard via LLM
    
    Args:
        campaign_data: Dictionary with campaign information
        llm_client: AWS Bedrock or Anthropic client
    
    Returns:
        Generated dashboard JSON
    """
    # Determine campaign type and generate appropriate prompt
    if "beauty" in campaign_data.get("industry", "").lower():
        prompt = generate_beauty_campaign_dashboard_prompt()
    elif "ecommerce" in campaign_data.get("industry", "").lower():
        prompt = generate_ecommerce_dashboard_prompt()
    elif "saas" in campaign_data.get("industry", "").lower():
        prompt = generate_saas_leadgen_dashboard_prompt()
    else:
        # Generic prompt
        prompt = DASHBOARD_GENERATION_PROMPT.format(**campaign_data)
    
    # Call LLM (assuming AWS Bedrock Claude)
    response = llm_client.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower for more consistent analysis
            "top_p": 0.9
        })
    )
    
    # Parse response
    response_body = json.loads(response['body'].read())
    dashboard_json = json.loads(response_body['content'][0]['text'])
    
    return dashboard_json


# Get metrics for specific category
def get_metrics_for_category(category_name: str):
    """
    Retrieve all metrics for a specific category
    """
    for category in MARKETING_DASHBOARD_TEMPLATE["categories"]:
        if category["category"] == category_name:
            return category["metrics"]
    return []


# Get all metric names
def get_all_metric_names():
    """
    Get a list of all available metric names
    """
    metrics = []
    for category in MARKETING_DASHBOARD_TEMPLATE["categories"]:
        for metric in category["metrics"]:
            metrics.append({
                "name": metric["metric_name"],
                "category": category["category"],
                "type": metric["metric_type"]
            })
    return metrics


# Example usage
if __name__ == "__main__":
    # Generate beauty campaign prompt
    beauty_prompt = generate_beauty_campaign_dashboard_prompt()
    print("=== BEAUTY CAMPAIGN PROMPT ===")
    print(beauty_prompt[:500] + "...")
    print("\n")
    
    # Generate e-commerce prompt
    ecommerce_prompt = generate_ecommerce_dashboard_prompt()
    print("=== E-COMMERCE CAMPAIGN PROMPT ===")
    print(ecommerce_prompt[:500] + "...")
    print("\n")
    
    # Get all available metrics
    all_metrics = get_all_metric_names()
    print(f"=== TOTAL AVAILABLE METRICS: {len(all_metrics)} ===")
    for metric in all_metrics[:10]:
        print(f"- {metric['name']} ({metric['category']})")

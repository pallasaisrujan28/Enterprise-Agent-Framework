"""
Marketing Campaign Dashboard Template
Defines metrics and structure for generating marketing dashboards
"""

# Complete Marketing Dashboard Metrics Template
MARKETING_DASHBOARD_TEMPLATE = {
    "template_name": "Marketing Campaign Dashboard",
    "version": "1.0",
    "categories": [
        {
            "category": "Campaign Overview",
            "metrics": [
                {
                    "metric_name": "Total Impressions",
                    "description": "Total number of times the campaign content was displayed",
                    "metric_type": "count",
                    "visualization": "big_number",
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Reach",
                    "description": "Unique number of people who saw the campaign",
                    "metric_type": "count",
                    "visualization": "big_number",
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Frequency",
                    "description": "Average number of times each person saw the campaign",
                    "metric_type": "ratio",
                    "calculation": "impressions / reach",
                    "visualization": "big_number",
                    "optimal_range": [3, 7]
                },
                {
                    "metric_name": "Campaign Duration",
                    "description": "Number of days the campaign has been running",
                    "metric_type": "count",
                    "visualization": "big_number"
                },
                {
                    "metric_name": "Budget Spent",
                    "description": "Total marketing budget spent to date",
                    "metric_type": "currency",
                    "visualization": "big_number",
                    "goal_comparison": True,
                    "alert_threshold": 0.9
                },
                {
                    "metric_name": "Budget Remaining",
                    "description": "Remaining marketing budget",
                    "metric_type": "currency",
                    "visualization": "big_number",
                    "alert_threshold": 0.1
                }
            ]
        },
        {
            "category": "Engagement Metrics",
            "metrics": [
                {
                    "metric_name": "Click-Through Rate (CTR)",
                    "description": "Percentage of impressions that resulted in clicks",
                    "metric_type": "percentage",
                    "calculation": "(clicks / impressions) * 100",
                    "visualization": "gauge",
                    "benchmark": 2.5,
                    "optimal_range": [2.0, 5.0],
                    "trend_analysis": True
                },
                {
                    "metric_name": "Engagement Rate",
                    "description": "Percentage of audience that interacted with content",
                    "metric_type": "percentage",
                    "calculation": "((likes + comments + shares) / reach) * 100",
                    "visualization": "gauge",
                    "benchmark": 3.0,
                    "optimal_range": [2.0, 6.0],
                    "trend_analysis": True
                },
                {
                    "metric_name": "Total Clicks",
                    "description": "Total number of clicks on campaign content",
                    "metric_type": "count",
                    "visualization": "line_chart",
                    "trend_analysis": True
                },
                {
                    "metric_name": "Video Views",
                    "description": "Total number of video views (if video campaign)",
                    "metric_type": "count",
                    "visualization": "bar_chart",
                    "trend_analysis": True
                },
                {
                    "metric_name": "Video Completion Rate",
                    "description": "Percentage of videos watched to completion",
                    "metric_type": "percentage",
                    "calculation": "(completed_views / total_views) * 100",
                    "visualization": "gauge",
                    "benchmark": 50.0,
                    "optimal_range": [40.0, 70.0]
                },
                {
                    "metric_name": "Social Shares",
                    "description": "Number of times content was shared",
                    "metric_type": "count",
                    "visualization": "bar_chart",
                    "trend_analysis": True
                },
                {
                    "metric_name": "Comments/Reactions",
                    "description": "Total comments and reactions on campaign content",
                    "metric_type": "count",
                    "visualization": "bar_chart",
                    "trend_analysis": True
                }
            ]
        },
        {
            "category": "Conversion Metrics",
            "metrics": [
                {
                    "metric_name": "Conversion Rate",
                    "description": "Percentage of clicks that resulted in conversions",
                    "metric_type": "percentage",
                    "calculation": "(conversions / clicks) * 100",
                    "visualization": "gauge",
                    "benchmark": 2.0,
                    "optimal_range": [1.5, 5.0],
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Total Conversions",
                    "description": "Total number of desired actions completed",
                    "metric_type": "count",
                    "visualization": "big_number",
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Cost Per Conversion (CPC)",
                    "description": "Average cost to acquire one conversion",
                    "metric_type": "currency",
                    "calculation": "budget_spent / conversions",
                    "visualization": "line_chart",
                    "benchmark": 50.0,
                    "trend_analysis": True,
                    "lower_is_better": True
                },
                {
                    "metric_name": "Return on Ad Spend (ROAS)",
                    "description": "Revenue generated per dollar spent",
                    "metric_type": "ratio",
                    "calculation": "revenue / budget_spent",
                    "visualization": "gauge",
                    "benchmark": 3.0,
                    "optimal_range": [2.5, 5.0],
                    "goal_comparison": True
                },
                {
                    "metric_name": "Revenue Generated",
                    "description": "Total revenue attributed to campaign",
                    "metric_type": "currency",
                    "visualization": "big_number",
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Lead Generation",
                    "description": "Total number of leads captured",
                    "metric_type": "count",
                    "visualization": "bar_chart",
                    "goal_comparison": True,
                    "trend_analysis": True
                },
                {
                    "metric_name": "Cost Per Lead (CPL)",
                    "description": "Average cost to acquire one lead",
                    "metric_type": "currency",
                    "calculation": "budget_spent / leads",
                    "visualization": "line_chart",
                    "trend_analysis": True,
                    "lower_is_better": True
                }
            ]
        },
        {
            "category": "Audience Insights",
            "metrics": [
                {
                    "metric_name": "Audience Demographics",
                    "description": "Breakdown by age, gender, location",
                    "metric_type": "segmentation",
                    "visualization": "pie_chart",
                    "dimensions": ["age_group", "gender", "location"]
                },
                {
                    "metric_name": "Device Breakdown",
                    "description": "Distribution across mobile, desktop, tablet",
                    "metric_type": "segmentation",
                    "visualization": "donut_chart",
                    "dimensions": ["device_type"]
                },
                {
                    "metric_name": "Top Performing Segments",
                    "description": "Audience segments with highest engagement",
                    "metric_type": "ranking",
                    "visualization": "horizontal_bar_chart",
                    "top_n": 5
                },
                {
                    "metric_name": "Geographic Performance",
                    "description": "Campaign performance by region/country",
                    "metric_type": "geographic",
                    "visualization": "heat_map",
                    "dimensions": ["country", "region", "city"]
                },
                {
                    "metric_name": "New vs Returning",
                    "description": "Ratio of new audience to returning audience",
                    "metric_type": "segmentation",
                    "visualization": "stacked_bar_chart"
                }
            ]
        },
        {
            "category": "Channel Performance",
            "metrics": [
                {
                    "metric_name": "Performance by Channel",
                    "description": "Comparison across social media, email, display, search",
                    "metric_type": "comparison",
                    "visualization": "grouped_bar_chart",
                    "dimensions": ["channel"],
                    "compare_metrics": ["impressions", "clicks", "conversions", "cost"]
                },
                {
                    "metric_name": "Best Performing Channel",
                    "description": "Channel with highest ROAS",
                    "metric_type": "ranking",
                    "visualization": "big_number"
                },
                {
                    "metric_name": "Channel Budget Allocation",
                    "description": "Budget distribution across channels",
                    "metric_type": "distribution",
                    "visualization": "pie_chart"
                },
                {
                    "metric_name": "Cross-Channel Attribution",
                    "description": "Customer journey across multiple channels",
                    "metric_type": "flow",
                    "visualization": "sankey_diagram"
                }
            ]
        },
        {
            "category": "Content Performance",
            "metrics": [
                {
                    "metric_name": "Top Performing Creative",
                    "description": "Best performing ad creatives/content",
                    "metric_type": "ranking",
                    "visualization": "card_grid",
                    "top_n": 5,
                    "show_thumbnail": True
                },
                {
                    "metric_name": "Message Resonance",
                    "description": "Effectiveness of different messaging themes",
                    "metric_type": "comparison",
                    "visualization": "radar_chart",
                    "dimensions": ["message_theme"]
                },
                {
                    "metric_name": "Content Type Performance",
                    "description": "Performance by content type (image, video, carousel)",
                    "metric_type": "comparison",
                    "visualization": "grouped_bar_chart",
                    "dimensions": ["content_type"]
                },
                {
                    "metric_name": "Call-to-Action (CTA) Performance",
                    "description": "Effectiveness of different CTAs",
                    "metric_type": "comparison",
                    "visualization": "horizontal_bar_chart",
                    "dimensions": ["cta_text"]
                }
            ]
        },
        {
            "category": "Time-Based Analysis",
            "metrics": [
                {
                    "metric_name": "Daily Performance Trend",
                    "description": "Key metrics tracked over time",
                    "metric_type": "time_series",
                    "visualization": "multi_line_chart",
                    "metrics": ["impressions", "clicks", "conversions"],
                    "granularity": "daily"
                },
                {
                    "metric_name": "Best Time to Post",
                    "description": "Optimal posting times based on engagement",
                    "metric_type": "time_analysis",
                    "visualization": "heat_map",
                    "dimensions": ["day_of_week", "hour_of_day"]
                },
                {
                    "metric_name": "Campaign Velocity",
                    "description": "Rate of key metric growth over time",
                    "metric_type": "velocity",
                    "visualization": "area_chart",
                    "metrics": ["conversions", "revenue"]
                },
                {
                    "metric_name": "Peak Performance Days",
                    "description": "Days with highest engagement/conversions",
                    "metric_type": "ranking",
                    "visualization": "bar_chart",
                    "top_n": 7
                }
            ]
        },
        {
            "category": "Cost Efficiency",
            "metrics": [
                {
                    "metric_name": "Cost Per Mille (CPM)",
                    "description": "Cost per 1000 impressions",
                    "metric_type": "currency",
                    "calculation": "(budget_spent / impressions) * 1000",
                    "visualization": "gauge",
                    "benchmark": 10.0,
                    "trend_analysis": True,
                    "lower_is_better": True
                },
                {
                    "metric_name": "Cost Per Click (CPC)",
                    "description": "Average cost per click",
                    "metric_type": "currency",
                    "calculation": "budget_spent / clicks",
                    "visualization": "gauge",
                    "benchmark": 1.5,
                    "trend_analysis": True,
                    "lower_is_better": True
                },
                {
                    "metric_name": "Cost Per Engagement",
                    "description": "Average cost per engagement action",
                    "metric_type": "currency",
                    "calculation": "budget_spent / total_engagements",
                    "visualization": "line_chart",
                    "trend_analysis": True,
                    "lower_is_better": True
                },
                {
                    "metric_name": "Budget Pacing",
                    "description": "Budget spend rate vs campaign timeline",
                    "metric_type": "percentage",
                    "calculation": "(budget_spent / total_budget) vs (days_elapsed / total_days)",
                    "visualization": "progress_bar",
                    "alert_threshold": 0.15
                }
            ]
        },
        {
            "category": "Brand Metrics",
            "metrics": [
                {
                    "metric_name": "Brand Awareness Lift",
                    "description": "Increase in brand awareness from campaign",
                    "metric_type": "percentage",
                    "visualization": "gauge",
                    "benchmark": 15.0,
                    "survey_based": True
                },
                {
                    "metric_name": "Brand Sentiment",
                    "description": "Positive vs negative sentiment in comments/mentions",
                    "metric_type": "sentiment",
                    "visualization": "sentiment_gauge",
                    "range": [-100, 100]
                },
                {
                    "metric_name": "Share of Voice",
                    "description": "Brand mentions vs competitor mentions",
                    "metric_type": "percentage",
                    "visualization": "pie_chart"
                },
                {
                    "metric_name": "Net Promoter Score (NPS)",
                    "description": "Likelihood of customers to recommend",
                    "metric_type": "score",
                    "visualization": "gauge",
                    "range": [-100, 100],
                    "benchmark": 50,
                    "survey_based": True
                }
            ]
        },
        {
            "category": "Predictive Insights",
            "metrics": [
                {
                    "metric_name": "Forecasted Conversions",
                    "description": "Predicted conversions by campaign end",
                    "metric_type": "forecast",
                    "visualization": "line_chart_with_forecast",
                    "confidence_interval": 0.95
                },
                {
                    "metric_name": "Projected ROI",
                    "description": "Expected return on investment",
                    "metric_type": "forecast",
                    "visualization": "big_number",
                    "confidence_interval": 0.95
                },
                {
                    "metric_name": "Recommended Budget Adjustment",
                    "description": "AI-suggested budget optimization",
                    "metric_type": "recommendation",
                    "visualization": "alert_card"
                },
                {
                    "metric_name": "Campaign Health Score",
                    "description": "Overall campaign performance score (0-100)",
                    "metric_type": "composite_score",
                    "calculation": "weighted_average(ctr, conversion_rate, roas, engagement_rate)",
                    "visualization": "gauge",
                    "range": [0, 100],
                    "thresholds": {
                        "poor": [0, 50],
                        "good": [50, 75],
                        "excellent": [75, 100]
                    }
                }
            ]
        }
    ]
}


# LLM Prompt Template for Dashboard Generation
DASHBOARD_GENERATION_PROMPT = """
You are an expert marketing analytics specialist. Generate a comprehensive dashboard analysis based on the following campaign data.

## Campaign Information:
- Campaign Name: {campaign_name}
- Campaign Objective: {campaign_objective}
- Target Audience: {target_audience}
- Campaign Duration: {start_date} to {end_date}
- Total Budget: ${total_budget}
- Industry: {industry}

## Raw Campaign Data:
{raw_data}

## Dashboard Requirements:
Generate insights and visualizations for the following metric categories:
{metric_categories}

## For Each Metric Category, Provide:

1. **Key Insights**: 3-5 bullet points highlighting the most important findings
2. **Performance Assessment**: How is the campaign performing (excellent/good/needs improvement)?
3. **Trend Analysis**: Identify positive or negative trends over time
4. **Actionable Recommendations**: 2-3 specific actions to improve performance
5. **Comparative Analysis**: How do metrics compare to industry benchmarks?
6. **Risk Alerts**: Any metrics that are underperforming or need immediate attention

## Output Format:
Structure your analysis in JSON format following this schema:

{{
  "dashboard_title": "Campaign Name Dashboard",
  "generated_at": "timestamp",
  "overall_health_score": 0-100,
  "executive_summary": {{
    "key_wins": ["win1", "win2", "win3"],
    "areas_of_concern": ["concern1", "concern2"],
    "top_recommendation": "most important action"
  }},
  "categories": [
    {{
      "category_name": "Campaign Overview",
      "metrics": [
        {{
          "metric_name": "Total Impressions",
          "current_value": 1500000,
          "goal_value": 2000000,
          "performance_vs_goal": 75,
          "trend": "increasing",
          "insight": "Impressions are growing steadily...",
          "visualization_data": {{...}}
        }}
      ],
      "category_insights": ["insight1", "insight2"],
      "recommendations": ["rec1", "rec2"]
    }}
  ],
  "alerts": [
    {{
      "severity": "high/medium/low",
      "metric": "metric_name",
      "message": "alert message",
      "recommendation": "suggested action"
    }}
  ]
}}

## Analysis Guidelines:
- Use data-driven insights, not generic statements
- Highlight both successes and areas for improvement
- Provide specific, actionable recommendations
- Include statistical significance where relevant
- Consider seasonal trends and external factors
- Compare performance across different audience segments
- Identify optimization opportunities

## Benchmarks to Use:
- Average CTR: 2.5%
- Average Conversion Rate: 2.0%
- Average Engagement Rate: 3.0%
- Target ROAS: 3.0
- Industry-specific benchmarks: {industry_benchmarks}

Generate the complete dashboard analysis now.
"""


# Specific prompt templates for different marketing channels
CHANNEL_SPECIFIC_PROMPTS = {
    "social_media": """
    Focus on:
    - Engagement rate (likes, comments, shares)
    - Follower growth
    - Viral content identification
    - Best posting times
    - Hashtag performance
    - Influencer impact
    - Social sentiment analysis
    """,
    
    "email_marketing": """
    Focus on:
    - Open rate
    - Click-through rate
    - Unsubscribe rate
    - Bounce rate
    - List growth rate
    - Email client performance
    - Subject line effectiveness
    - A/B test results
    """,
    
    "paid_search": """
    Focus on:
    - Quality Score
    - Ad Rank
    - Keyword performance
    - Search impression share
    - Negative keyword opportunities
    - Bid strategy effectiveness
    - Landing page relevance
    """,
    
    "display_advertising": """
    Focus on:
    - Viewability rate
    - Ad position impact
    - Placement performance
    - Creative fatigue
    - Retargeting effectiveness
    - Banner size performance
    """,
    
    "video_marketing": """
    Focus on:
    - View-through rate
    - Average watch time
    - Drop-off points
    - Completion rate by video length
    - CTA click rate
    - Player type performance
    """
}


# Dashboard visualization preferences
VISUALIZATION_CONFIG = {
    "color_scheme": {
        "primary": "#4F46E5",      # Indigo
        "success": "#10B981",      # Green
        "warning": "#F59E0B",      # Amber
        "danger": "#EF4444",       # Red
        "info": "#3B82F6",         # Blue
        "neutral": "#6B7280"       # Gray
    },
    "chart_types": {
        "big_number": {"component": "StatCard", "size": "large"},
        "gauge": {"component": "GaugeChart", "max_value": 100},
        "line_chart": {"component": "LineChart", "smooth": True},
        "bar_chart": {"component": "BarChart", "orientation": "vertical"},
        "pie_chart": {"component": "PieChart", "show_legend": True},
        "heat_map": {"component": "HeatMap", "color_scale": "gradient"},
        "progress_bar": {"component": "ProgressBar", "animated": True}
    },
    "responsive_breakpoints": {
        "mobile": "< 640px",
        "tablet": "640px - 1024px",
        "desktop": "> 1024px"
    }
}

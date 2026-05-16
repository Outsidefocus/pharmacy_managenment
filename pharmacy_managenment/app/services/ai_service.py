import openai
import google.generativeai as genai
from typing import Dict, List, Optional, Any
import json
import requests
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AIService:
  def __init__(self):
    self.openai_api_key = settings.OPENAI_API_KEY
    self.google_api_key = settings.GOOGLE_API_KEY
    self.openai_client = openai.OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None

    if self.google_api_key:
      genai.configure(api_key=self.google_api_key)
      self.gemini_model = genai.GenerativeModel('gemini-pro')
    else:
      self.gemini_model = None

  async def analyze_market_trends(self, product_data: List[Dict]) -> Dict:
    """Analyze market trends using AI"""
    try:
      if not self.openai_client:
        return self._generate_mock_analysis(product_data)

      prompt = f"""
            Analyze the following pharmacy product data and provide insights:
            {json.dumps(product_data[:10], indent=2)}

            Provide analysis in JSON format with:
            1. top_selling_categories
            2. seasonal_trends
            3. pricing_recommendations
            4. stock_optimization_suggestions
            5. emerging_market_opportunities
            """

      response = self.openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "You are a pharmacy market analyst."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
      )

      analysis_text = response.choices[0].message.content
      return self._parse_analysis_response(analysis_text)

    except Exception as e:
      logger.error(f"Error in market analysis: {e}")
      return self._generate_mock_analysis(product_data)

  async def predict_demand(self, product_id: int, historical_data: List[Dict]) -> Dict:
    """Predict future demand for a product"""
    try:
      if not self.gemini_model:
        return self._generate_mock_prediction(historical_data)

      prompt = f"""
            Based on this historical sales data, predict next month's demand:
            {json.dumps(historical_data, indent=2)}

            Consider:
            - Seasonality
            - Growth trends
            - External factors (holidays, weather)

            Provide prediction in JSON format with:
            - predicted_quantity
            - confidence_level
            - factors_considered
            - recommendations
            """

      response = self.gemini_model.generate_content(prompt)

      if response.text:
        return self._parse_prediction_response(response.text)
      else:
        return self._generate_mock_prediction(historical_data)

    except Exception as e:
      logger.error(f"Error in demand prediction: {e}")
      return self._generate_mock_prediction(historical_data)

  async def generate_marketing_insights(self, customer_data: List[Dict]) -> Dict:
    """Generate marketing insights from customer data"""
    try:
      if not self.openai_client:
        return self._generate_mock_insights()

      prompt = f"""
            Analyze customer purchase patterns:
            {json.dumps(customer_data[:5], indent=2)}

            Provide marketing insights including:
            1. customer_segments
            2. cross_sell_opportunities
            3. loyalty_program_suggestions
            4. personalized_promotion_ideas
            5. retention_strategies
            """

      response = self.openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "You are a pharmacy marketing expert."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800
      )

      insights_text = response.choices[0].message.content
      return self._parse_insights_response(insights_text)

    except Exception as e:
      logger.error(f"Error generating insights: {e}")
      return self._generate_mock_insights()

  async def optimize_pricing(self, product_info: Dict, market_data: Dict) -> Dict:
    """Optimize product pricing using AI"""
    try:
      if not self.gemini_model:
        return self._generate_mock_pricing()

      prompt = f"""
            Optimize pricing for pharmacy product:
            Product Info: {json.dumps(product_info, indent=2)}
            Market Data: {json.dumps(market_data, indent=2)}

            Provide optimized pricing strategy with:
            - recommended_price
            - pricing_strategy
            - competitive_analysis
            - implementation_steps
            - expected_impact
            """

      response = self.gemini_model.generate_content(prompt)

      if response.text:
        return self._parse_pricing_response(response.text)
      else:
        return self._generate_mock_pricing()

    except Exception as e:
      logger.error(f"Error in pricing optimization: {e}")
      return self._generate_mock_pricing()

  async def get_google_market_data(self, product_name: str) -> Dict:
    """Get market data from Google Trends/Search"""
    try:
      # Using Google Custom Search API as an example
      url = "https://www.googleapis.com/customsearch/v1"
      params = {
        "key": self.google_api_key,
        "cx": "YOUR_SEARCH_ENGINE_ID",  # You need to create this
        "q": f"pharmacy {product_name} market trends 2024",
        "num": 5
      }

      response = requests.get(url, params=params)
      if response.status_code == 200:
        return response.json()
      else:
        return {"error": "Failed to fetch market data"}

    except Exception as e:
      logger.error(f"Error fetching Google data: {e}")
      return {"error": str(e)}

  def _generate_mock_analysis(self, product_data: List[Dict]) -> Dict:
    """Generate mock analysis when AI service is unavailable"""
    return {
      "top_selling_categories": ["Antibiotics", "Pain Relief", "Vitamins"],
      "seasonal_trends": {
        "winter": ["Cold & Flu", "Vitamin D"],
        "summer": ["Allergy", "Sunscreen"]
      },
      "pricing_recommendations": [
        {"product": "Paracetamol", "current_price": 5.99, "suggested_price": 6.49},
        {"product": "Vitamin C", "current_price": 12.99, "suggested_price": 11.99}
      ],
      "stock_optimization_suggestions": [
        "Increase stock of Antibiotics by 20%",
        "Reduce stock of seasonal products post-season"
      ],
      "emerging_market_opportunities": [
        "Wellness products",
        "Telemedicine integration",
        "Personalized supplements"
      ]
    }

  def _parse_analysis_response(self, text: str) -> Dict:
    """Parse AI response text to structured JSON"""
    try:
      # Extract JSON from text
      if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0]
      elif "```" in text:
        json_str = text.split("```")[1].split("```")[0]
      else:
        json_str = text

      return json.loads(json_str)
    except:
      # Fallback to extracting key information
      return {"raw_analysis": text[:500]}

  def _generate_mock_prediction(self, historical_data: List[Dict]) -> Dict:
    """Generate mock prediction"""
    last_month = historical_data[-1] if historical_data else {"quantity": 100}
    base_qty = last_month.get("quantity", 100)

    return {
      "predicted_quantity": int(base_qty * 1.1),
      "confidence_level": 0.75,
      "factors_considered": ["Historical trend", "Seasonality"],
      "recommendations": ["Maintain current stock levels", "Monitor weekly sales"]
    }

  def _generate_mock_insights(self) -> Dict:
    """Generate mock marketing insights"""
    return {
      "customer_segments": [
        {"segment": "Regular customers", "percentage": 40},
        {"segment": "Occasional buyers", "percentage": 35},
        {"segment": "New customers", "percentage": 25}
      ],
      "cross_sell_opportunities": [
        "Customers buying pain relief often buy vitamins",
        "Antibiotic prescriptions can be paired with probiotics"
      ],
      "personalized_promotion_ideas": [
        "Loyalty discounts for frequent buyers",
        "Bundle offers for related products"
      ]
    }

  def _generate_mock_pricing(self) -> Dict:
    """Generate mock pricing optimization"""
    return {
      "recommended_price": 15.99,
      "pricing_strategy": "Competitive pricing with value-added services",
      "competitive_analysis": {
        "average_market_price": 16.50,
        "lowest_price": 14.99,
        "highest_price": 18.99
      },
      "implementation_steps": [
        "Monitor competitor prices weekly",
        "Adjust based on inventory levels",
        "Offer bundle discounts"
      ]
    }
"""
News and Social Media Data Source
Provides Fear & Greed Index for market sentiment analysis
"""

from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from loguru import logger


class NewsSocialDataSource:
    """
    News and social media data source.

    Provides:
    - Fear & Greed Index (0-100)
    - Market sentiment classification
    """

    def __init__(self):
        """Initialize news/social data source."""
        self.session: Optional[httpx.AsyncClient] = None

        # Fear & Greed Index API (free, no API key needed)
        self.sentiment_api_url = "https://api.alternative.me/fng/"

        # Cache
        self._last_sentiment: Optional[Dict[str, Any]] = None
        self._last_sentiment_date: Optional[str] = None  # 按日期缓存

        logger.info("Initialized News/Social data source (Fear & Greed only)")

    async def connect(self) -> bool:
        """
        Connect to API.

        Returns:
            True if connection successful
        """
        try:
            self.session = httpx.AsyncClient(
                timeout=30.0, headers={"User-Agent": "PolymarketBot/1.0"}
            )

            # Test connection with Fear & Greed Index
            response = await self.session.get(self.sentiment_api_url)
            response.raise_for_status()

            logger.info("✓ Connected to Fear & Greed API")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Fear & Greed API: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connections."""
        if self.session:
            await self.session.aclose()
            logger.info("Disconnected from Fear & Greed API")

    async def get_fear_greed_index(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get Fear & Greed Index (0-100).
        Cached by date since it only updates once per day.

        Args:
            force_refresh: Force refresh cache

        Returns:
            Dict with value, classification, and timestamp
        """
        today = datetime.now().date().isoformat()

        # Return cached value if same day and not forcing refresh
        if (
            not force_refresh
            and self._last_sentiment
            and self._last_sentiment_date == today
        ):
            logger.debug(f"Using cached Fear & Greed (date: {today})")
            return self._last_sentiment

        try:
            response = await self.session.get(self.sentiment_api_url)
            response.raise_for_status()

            data = response.json()
            current = data["data"][0]

            sentiment = {
                "timestamp": datetime.fromtimestamp(int(current["timestamp"])),
                "value": int(current["value"]),  # 0-100
                "classification": current[
                    "value_classification"
                ],  # "Extreme Fear", etc.
                "time_until_update": current.get("time_until_update"),
            }

            self._last_sentiment = sentiment
            self._last_sentiment_date = today

            logger.info(
                f"Fear & Greed Index: {sentiment['value']} ({sentiment['classification']})"
            )
            return sentiment

        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            # Return cached value if available
            if self._last_sentiment:
                logger.warning("Returning cached Fear & Greed (stale)")
                return self._last_sentiment
            return None

    async def get_sentiment_score(self, force_refresh: bool = False) -> Optional[float]:
        """
        Get sentiment score (0-100).
        0 = Extreme Fear (BULLISH signal), 100 = Extreme Greed (BEARISH signal)

        Args:
            force_refresh: Force refresh cache

        Returns:
            Sentiment score (0-100)
        """
        fg_data = await self.get_fear_greed_index(force_refresh=force_refresh)
        if not fg_data:
            return None

        score = float(fg_data["value"])

        # Log interpretation for context
        if score < 25:
            logger.info(
                f"Sentiment: Extreme Fear ({score:.0f}) → BULLISH signal expected"
            )
        elif score > 75:
            logger.info(
                f"Sentiment: Extreme Greed ({score:.0f}) → BEARISH signal expected"
            )
        elif score < 45:
            logger.info(f"Sentiment: Fear ({score:.0f})")
        elif score > 55:
            logger.info(f"Sentiment: Greed ({score:.0f})")
        else:
            logger.info(f"Sentiment: Neutral ({score:.0f})")

        return score

    @property
    def last_sentiment(self) -> Optional[Dict[str, Any]]:
        """Get cached sentiment data."""
        return self._last_sentiment

    async def health_check(self) -> bool:
        """
        Check if data source is healthy.

        Returns:
            True if healthy
        """
        try:
            sentiment = await self.get_fear_greed_index()
            return sentiment is not None
        except Exception as e:
            logger.error(e)
            return False


# Singleton instance
_news_instance: Optional[NewsSocialDataSource] = None


def get_news_social_source() -> NewsSocialDataSource:
    """Get singleton instance of News/Social data source."""
    global _news_instance
    if _news_instance is None:
        _news_instance = NewsSocialDataSource()
    return _news_instance

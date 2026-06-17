import json
import redis
from typing import List, Optional, Dict, Any
from src.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=20, decode_responses=True)
redis_client = redis.Redis(connection_pool=redis_pool)


class CacheService:
    @staticmethod
    def cache_prompt_template(template_id: str, structure_scheme: List[Dict[str, Any]]) -> None:
        """Caches structural matrices inside Redis securely using type-safe structures."""
        # 🌟 FIX BUG 1: Type safety applied
        key = f"template:{template_id}"
        redis_client.setex(key, 86400, json.dumps(structure_scheme))

    @staticmethod
    def get_cached_template(template_id: str) -> Optional[List[Dict[str, Any]]]:
        try:
            data = redis_client.get(f"template:{template_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"[CACHE WARNING] Redis connection failure, bypassing cleanly: {str(e)}")
            return None

    @staticmethod
    def index_assignment_for_search(school_id: str, assignment_id: str, title: str, topic: str) -> None:
        index_key = f"search:school:{school_id}"
        payload = {"id": assignment_id, "title": title, "topic": topic}
        redis_client.hset(index_key, assignment_id, json.dumps(payload))

    @staticmethod
    def search_assignments(school_id: str, query: str) -> List[Dict[str, Any]]:
        index_key = f"search:school:{school_id}"
        try:
            all_items = redis_client.hgetall(index_key)
        except Exception:
            return []  # Fall back safely to empty array if cache chokes

        results = []
        clean_query = query.lower()
        for data_str in all_items.values():
            item = json.loads(data_str)
            if clean_query in item["title"].lower() or clean_query in item["topic"].lower():
                results.append(item)
        return results

    @staticmethod
    def remove_from_search(school_id: str, assignment_id: str) -> None:
        redis_client.hdel(f"search:school:{school_id}", assignment_id)

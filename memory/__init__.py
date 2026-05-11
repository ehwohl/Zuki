from .history_manager import HistoryManager
from .user_profile import UserProfile

__all__ = ["HistoryManager", "UserProfile"]

# SupabaseMemoryProvider und ZukiMemory sind verfügbar, aber nicht aktiv geladen.
# Aktivieren wenn supabase installiert ist:
#   from .zuki_memory import ZukiMemory
#   from .supabase_provider import SupabaseMemoryProvider

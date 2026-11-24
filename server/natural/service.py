"""Composition root; shares the existing database, security service and AI router."""
from server.natural.store import NaturalStore
from server.natural.settings import SettingsManager
from server.natural.memory import MemoryManager
from server.natural.conversation import NaturalConversationManager


class NaturalService:
    def __init__(self,database,security,chat,automation):
        self.store=NaturalStore(database,security,chat.store.clean)
        self.settings=SettingsManager(self.store)
        self.memory=MemoryManager(self.store)
        self.security,self.chat,self.automation=security,chat,automation
        self.conversations=NaturalConversationManager(self.store,self.settings,chat)

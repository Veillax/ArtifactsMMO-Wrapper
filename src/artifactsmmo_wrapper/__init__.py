import requests
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, timezone

from threading import Lock
from functools import wraps
import math
import re

debug=False

logger = logging.getLogger(__name__)

# Define the logging format you want to apply
formatter = logging.Formatter(
    fmt="\33[34m[%(levelname)s] %(asctime)s - %(char)s:\33[0m %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Create a handler (e.g., StreamHandler for console output) and set its format
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Attach the handler to the parent logger (if not already present)
if not logger.hasHandlers():
    logger.addHandler(console_handler)

# --- Exceptions ---

# Exception class with logging
class APIException(Exception):
    """Base exception class for API errors"""
    
    # Log the exception when it is raised
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"APIException raised: {message}")

    class CharacterInCooldown(Exception):
        def __init__(self, message="Character is in cooldown"):
            super().__init__(message)
            logger.warning(f"CharacterInCooldown: {message}")

    class NotFound(Exception):
        def __init__(self, message="Resource not found"):
            super().__init__(message)
            logger.error(f"NotFound: {message}")

    class ActionAlreadyInProgress(Exception):
        def __init__(self, message="Action is already in progress"):
            super().__init__(message)
            logger.warning(f"ActionAlreadyInProgress: {message}")

    class CharacterNotFound(Exception):
        def __init__(self, message="Character not found"):
            super().__init__(message)
            logger.error(f"CharacterNotFound: {message}")

    class TooLowLevel(Exception):
        def __init__(self, message="Level is too low"):
            super().__init__(message)
            logger.error(f"TooLowLevel: {message}")

    class InventoryFull(Exception):
        def __init__(self, message="Inventory is full"):
            super().__init__(message)
            logger.warning(f"InventoryFull: {message}")

    class MapItemNotFound(Exception):
        def __init__(self, message="Map item not found"):
            super().__init__(message)
            logger.error(f"MapItemNotFound: {message}")

    class InsufficientQuantity(Exception):
        def __init__(self, message="Insufficient quantity"):
            super().__init__(message)
            logger.warning(f"InsufficientQuantity: {message}")

    class GETooMany(Exception):
        def __init__(self, message="Too many GE items"):
            super().__init__(message)
            logger.error(f"GETooMany: {message}")

    class GENoStock(Exception):
        def __init__(self, message="No stock available"):
            super().__init__(message)
            logger.error(f"GENoStock: {message}")

    class GENoItem(Exception):
        def __init__(self, message="Item not found in GE"):
            super().__init__(message)
            logger.error(f"GENoItem: {message}")

    class TransactionInProgress(Exception):
        def __init__(self, message="Transaction already in progress"):
            super().__init__(message)
            logger.warning(f"TransactionInProgress: {message}")

    class InsufficientGold(Exception):
        def __init__(self, message="Not enough gold"):
            super().__init__(message)
            logger.warning(f"InsufficientGold: {message}")

    class TaskMasterNoTask(Exception):
        def __init__(self, message="No task assigned to TaskMaster"):
            super().__init__(message)
            logger.error(f"TaskMasterNoTask: {message}")

    class TaskMasterAlreadyHasTask(Exception):
        def __init__(self, message="TaskMaster already has a task"):
            super().__init__(message)
            logger.warning(f"TaskMasterAlreadyHasTask: {message}")

    class TaskMasterTaskNotComplete(Exception):
        def __init__(self, message="TaskMaster task is not complete"):
            super().__init__(message)
            logger.error(f"TaskMasterTaskNotComplete: {message}")

    class TaskMasterTaskMissing(Exception):
        def __init__(self, message="TaskMaster task is missing"):
            super().__init__(message)
            logger.error(f"TaskMasterTaskMissing: {message}")

    class TaskMasterTaskAlreadyCompleted(Exception):
        def __init__(self, message="TaskMaster task already completed"):
            super().__init__(message)
            logger.warning(f"TaskMasterTaskAlreadyCompleted: {message}")

    class RecyclingItemNotRecyclable(Exception):
        def __init__(self, message="Item is not recyclable"):
            super().__init__(message)
            logger.error(f"RecyclingItemNotRecyclable: {message}")

    class EquipmentTooMany(Exception):
        def __init__(self, message="Too many equipment items"):
            super().__init__(message)
            logger.warning(f"EquipmentTooMany: {message}")

    class EquipmentAlreadyEquipped(Exception):
        def __init__(self, message="Equipment already equipped"):
            super().__init__(message)
            logger.warning(f"EquipmentAlreadyEquipped: {message}")

    class EquipmentSlot(Exception):
        def __init__(self, message="Invalid equipment slot"):
            super().__init__(message)
            logger.error(f"EquipmentSlot: {message}")

    class AlreadyAtDestination(Exception):
        def __init__(self, message="Already at destination"):
            super().__init__(message)
            logger.info(f"AlreadyAtDestination: {message}")

    class BankFull(Exception):
        def __init__(self, message="Bank is full"):
            super().__init__(message)
            logger.warning(f"BankFull: {message}")

    class TokenMissingorEmpty(Exception):
        def __init__(self, message="Token is missing or empty"):
            super().__init__(message)
            logger.error(f"TokenMissingorEmpty: {message}")
    
    class NameAlreadyUsed(Exception):
        def __init__(self, message="Name already used"):
            super().__init__(message)
            logger.error(f"NameAlreadyUsed: {message}")
    
    class MaxCharactersReached(Exception):
        def __init__(self, message="Max characters reached"):
            super().__init__(message)
            logger.warning(f"MaxCharactersReached: {message}")


class CooldownManager:
    """
    A class to manage cooldowns for different operations using an expiration timestamp.
    """
    def __init__(self):
        self.lock = Lock()
        self.cooldown_expiration_time = None
        self.logger = None

    def is_on_cooldown(self) -> bool:
        """Check if currently on cooldown based on expiration time."""
        with self.lock:
            if self.cooldown_expiration_time is None:
                return False  # No cooldown set
            # Check if current time is before the expiration time
            return datetime.now(timezone.utc) < self.cooldown_expiration_time

    def set_cooldown_from_expiration(self, expiration_time_str: str) -> None:
        """Set cooldown based on an ISO 8601 expiration time string."""
        with self.lock:
            # Parse the expiration time string
            self.cooldown_expiration_time = datetime.fromisoformat(expiration_time_str)

    def wait_for_cooldown(self, logger=None, char=None) -> None:
        """Wait until the cooldown expires."""
        if self.is_on_cooldown():
            remaining = (self.cooldown_expiration_time - datetime.now(timezone.utc)).total_seconds()
            if logger:
                if char:
                    logger.debug(f"Waiting for cooldown... ({remaining:.1f} seconds)", extra={"char": char.name})
                else:
                    logger.debug(f"Waiting for cooldown... ({remaining:.1f} seconds)", extra={"char": "Unknown"})
            while self.is_on_cooldown():
                remaining = (self.cooldown_expiration_time - datetime.now(timezone.utc)).total_seconds()
                time.sleep(min(remaining, 0.1))  # Sleep in small intervals

def with_cooldown(func):
    """
    Decorator to apply cooldown management to a method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_cooldown_manager'):
            self._cooldown_manager = CooldownManager()
        
        # Before executing the action, check if the character is on cooldown
        source = kwargs.get('source')
        method = kwargs.get('method')
        
        # Skip cooldown for "get_character" source to allow fetching character data without waiting
        if source != "get_character":
            # Ensure cooldown manager is up to date with the character's cooldown expiration time
            if hasattr(self, 'char') and hasattr(self.char, 'cooldown_expiration'):
                self._cooldown_manager.set_cooldown_from_expiration(self.char.cooldown_expiration)

            # Wait for the cooldown to finish before calling the function
            self._cooldown_manager.wait_for_cooldown(logger=self.logger, char=self.char)

        # Now execute the function after confirming cooldown is finished
        result = func(self, *args, **kwargs)

        # Update the cooldown after the action if needed (depending on your business logic)
        if method not in ["GET", None, "None"]:
            # Set cooldown after the operation, if the character has a cooldown expiration
            if hasattr(self, 'char') and hasattr(self.char, 'cooldown_expiration'):
                self._cooldown_manager.set_cooldown_from_expiration(self.char.cooldown_expiration)
        
        return result
    return wrapper


# --- Dataclasses ---
@dataclass
class Position:
    """Represents a position on a 2D grid."""
    x: int
    y: int

    def __repr__(self) -> str:
        """String representation of the position in (x, y) format."""
        return f"({self.x}, {self.y})"

    def dist(self, other: 'Position') -> int:
        """
        Calculate the Manhattan distance to another position.
        
        Args:
            other (Position): The other position to calculate distance to.
        
        Returns:
            int: Manhattan distance to the other position.
        """
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __iter__(self):
        yield self.x
        yield self.y


@dataclass
class Drop:
    code: str
    rate: int
    min_quantity: int
    max_quantity: int

@dataclass
class ContentMap:
    name: str
    code: str
    level: int
    skill: str
    pos: Position
    drops: List[Drop]

    def __iter__(self):
        yield self.pos.x
        yield self.pos.y

    def __repr__(self) -> str:
        return f"{self.name} ({self.code}) at {self.pos}\n  Requires {self.skill} level {self.level}"
    

@dataclass
class ContentMaps:
    salmon_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Salmon Fishing Spot", code="salmon_fishing_spot", level=40, skill="fishing", pos=Position(-2, -4), drops=[Drop(code="salmon", rate=1, min_quantity=1, max_quantity=1), Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)]))
    goblin_wolfrider: ContentMap = field(default_factory=lambda: ContentMap(name="Goblin Wolfrider", code="goblin_wolfrider", level=40, skill="combat", pos=Position(6, -4), drops=[Drop(code="broken_sword", rate=24, min_quantity=1, max_quantity=1), Drop(code="wolfrider_hair", rate=12, min_quantity=1, max_quantity=1)]))
    orc: ContentMap = field(default_factory=lambda: ContentMap(name="Orc", code="orc", level=38, skill="combat", pos=Position(7, -2), drops=[Drop(code="orc_skin", rate=12, min_quantity=1, max_quantity=1)]))
    ogre: ContentMap = field(default_factory=lambda: ContentMap(name="Ogre", code="ogre", level=20, skill="combat", pos=Position(8, -2), drops=[Drop(code="ogre_eye", rate=12, min_quantity=1, max_quantity=1), Drop(code="ogre_skin", rate=12, min_quantity=1, max_quantity=1), Drop(code="wooden_club", rate=100, min_quantity=1, max_quantity=1)]))
    pig: ContentMap = field(default_factory=lambda: ContentMap(name="Pig", code="pig", level=19, skill="combat", pos=Position(-3, -3), drops=[Drop(code="pig_skin", rate=12, min_quantity=1, max_quantity=1)]))
    woodcutting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Woodcutting", code="woodcutting", level=1, skill=None, pos=Position(-2, -3), drops=[]))
    gold_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Gold Rocks", code="gold_rocks", level=30, skill="mining", pos=Position(6, -3), drops=[Drop(code="gold_ore", rate=1, min_quantity=1, max_quantity=1), Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1), Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1), Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)]))
    cyclops: ContentMap = field(default_factory=lambda: ContentMap(name="Cyclops", code="cyclops", level=25, skill="combat", pos=Position(7, -3), drops=[Drop(code="cyclops_eye", rate=12, min_quantity=1, max_quantity=1)]))
    blue_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Blue Slime", code="blue_slime", level=6, skill="combat", pos=Position(0, -2), drops=[Drop(code="blue_slimeball", rate=12, min_quantity=1, max_quantity=1), Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)]))
    yellow_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Yellow Slime", code="yellow_slime", level=2, skill="combat", pos=Position(1, -2), drops=[Drop(code="yellow_slimeball", rate=12, min_quantity=1, max_quantity=1), Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)]))
    red_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Red Slime", code="red_slime", level=7, skill="combat", pos=Position(1, -1), drops=[Drop(code="red_slimeball", rate=12, min_quantity=1, max_quantity=1), Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)]))
    green_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Green Slime", code="green_slime", level=4, skill="combat", pos=Position(0, -1), drops=[Drop(code="green_slimeball", rate=12, min_quantity=1, max_quantity=1), Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)]))
    goblin: ContentMap = field(default_factory=lambda: ContentMap(name="Goblin", code="goblin", level=35, skill="combat", pos=Position(6, -2), drops=[Drop(code="goblin_tooth", rate=12, min_quantity=1, max_quantity=1), Drop(code="goblin_eye", rate=12, min_quantity=1, max_quantity=1)]))
    wolf: ContentMap = field(default_factory=lambda: ContentMap(name="Wolf", code="wolf", level=15, skill="combat", pos=Position(-2, 1), drops=[Drop(code="raw_wolf_meat", rate=10, min_quantity=1, max_quantity=1), Drop(code="wolf_bone", rate=12, min_quantity=1, max_quantity=1), Drop(code="wolf_hair", rate=12, min_quantity=1, max_quantity=1)]))
    ash_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Ash Tree", code="ash_tree", level=1, skill="woodcutting", pos=Position(-1, 0), drops=[Drop(code="ash_wood", rate=1, min_quantity=1, max_quantity=1), Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)]))
    copper_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Copper Rocks", code="copper_rocks", level=1, skill="mining", pos=Position(2, 0), drops=[Drop(code="copper_ore", rate=1, min_quantity=1, max_quantity=1), Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1), Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1), Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)]))
    chicken: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="chicken", level=1, skill="combat", pos=Position(0, 1), drops=[Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1), Drop(code="egg", rate=12, min_quantity=1, max_quantity=1), Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)]))
    cooking_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Cooking", code="cooking", level=1, skill=None, pos=Position(1, 1), drops=[]))
    weaponcrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Weaponcrafting", code="weaponcrafting", level=1, skill=None, pos=Position(2, 1), drops=[]))
    gearcrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Gearcrafting", code="gearcrafting", level=1, skill=None, pos=Position(3, 1), drops=[]))
    bank: ContentMap = field(default_factory=lambda: ContentMap(name="Bank", code="bank", level=1, skill=None, pos=Position(4, 1), drops=[Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1), Drop(code="egg", rate=12, min_quantity=1, max_quantity=1), Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)]))
    grand_exchange: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="grand_exchange", level=1, skill="combat", pos=Position(5, 1), drops=[Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1), Drop(code="egg", rate=12, min_quantity=1, max_quantity=1), Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)]))
    owlbear: ContentMap = field(default_factory=lambda: ContentMap(name="Owlbear", code="owlbear", level=30, skill="combat", pos=Position(10, 1), drops=[Drop(code="owlbear_hair", rate=12, min_quantity=1, max_quantity=1)]))      
    cow: ContentMap = field(default_factory=lambda: ContentMap(name="Cow", code="cow", level=8, skill="combat", pos=Position(0, 2), drops=[Drop(code="raw_beef", rate=10, min_quantity=1, max_quantity=1), Drop(code="milk_bucket", rate=12, min_quantity=1, max_quantity=1), Drop(code="cowhide", rate=8, min_quantity=1, max_quantity=1)]))
    taskmaster_monsters: ContentMap = field(default_factory=lambda: ContentMap(name="Taskmaster of Monsters", code="monsters", level=8, skill="combat", pos=Position(1, 2), drops=[]))
    sunflower: ContentMap = field(default_factory=lambda: ContentMap(name="Sunflower", code="sunflower", level=1, skill="alchemy", pos=Position(2, 2), drops=[Drop(code="sunflower", rate=1, min_quantity=1, max_quantity=1)]))     
    gudgeon_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Gudgeon Fishing Spot", code="gudgeon_fishing_spot", level=1, skill="fishing", pos=Position(4, 2), drops=[Drop(code="gudgeon", rate=1, min_quantity=1, max_quantity=1), Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)]))
    shrimp_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Shrimp Fishing Spot", code="shrimp_fishing_spot", level=10, skill="fishing", pos=Position(5, 2), drops=[Drop(code="shrimp", rate=1, min_quantity=1, max_quantity=1), Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)]))
    jewelrycrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Jewelrycrafting", code="jewelrycrafting", level=1, skill=None, pos=Position(1, 3), drops=[]))
    alchemy_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Alchemy", code="alchemy", level=1, skill=None, pos=Position(2, 3), drops=[]))       
    mushmush: ContentMap = field(default_factory=lambda: ContentMap(name="Mushmush", code="mushmush", level=10, skill="combat", pos=Position(5, 3), drops=[Drop(code="mushroom", rate=12, min_quantity=1, max_quantity=1), Drop(code="forest_ring", rate=100, min_quantity=1, max_quantity=1)]))
    flying_serpent: ContentMap = field(default_factory=lambda: ContentMap(name="Flying Serpent", code="flying_serpent", level=12, skill="combat", pos=Position(5, 4), drops=[Drop(code="flying_wing", rate=12, min_quantity=1, max_quantity=1), Drop(code="serpent_skin", rate=12, min_quantity=1, max_quantity=1), Drop(code="forest_ring", rate=100, min_quantity=1, max_quantity=1)]))
    mining_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Mining", code="mining", level=1, skill=None, pos=Position(1, 5), drops=[]))
    birch_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Birch Tree", code="birch_tree", level=20, skill=None, pos=Position(3, 5), drops=[Drop(code="birch_wood", rate=1, min_quantity=1, max_quantity=1), Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)]))
    coal_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Coal Rocks", code="coal_rocks", level=20, skill="mining", pos=Position(1, 6), drops=[Drop(code="coal", rate=1, min_quantity=1, max_quantity=1), Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1), Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1), Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1), Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1), Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)]))
    spruce_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Spruce Tree", code="spruce_tree", level=10, skill="woodcutting", pos=Position(2, 6), drops=[Drop(code="spruce_wood", rate=1, min_quantity=1, max_quantity=1), Drop(code="sap", rate=10, min_quantity=1, max_quantity=1), Drop(code="apple", rate=10, min_quantity=1, max_quantity=1)]))
    skeleton: ContentMap = field(default_factory=lambda: ContentMap(name="Skeleton", code="skeleton", level=18, skill="combat", pos=Position(8, 6), drops=[Drop(code="skeleton_bone", rate=12, min_quantity=1, max_quantity=1), Drop(code="skeleton_skull", rate=16, min_quantity=1, max_quantity=1)]))
    dead_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Dead Tree", code="dead_tree", level=30, skill="woodcutting", pos=Position(9, 6), drops=[Drop(code="dead_wood", rate=1, min_quantity=1, max_quantity=1), Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)]))
    vampire: ContentMap = field(default_factory=lambda: ContentMap(name="Vampire", code="vampire", level=24, skill="combat", pos=Position(10, 6), drops=[Drop(code="vampire_blood", rate=12, min_quantity=1, max_quantity=1)]))     
    iron_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Iron Rocks", code="iron_rocks", level=10, skill="mining", pos=Position(1, 7), drops=[Drop(code="iron_ore", rate=1, min_quantity=1, max_quantity=1), Drop(code="topaz_stone", rate=500, min_quantity=1, max_quantity=1), Drop(code="topaz", rate=4000, min_quantity=1, max_quantity=1), Drop(code="emerald", rate=4000, min_quantity=1, max_quantity=1), Drop(code="emerald_stone", rate=500, min_quantity=1, max_quantity=1), Drop(code="ruby", rate=4000, min_quantity=1, max_quantity=1), Drop(code="ruby_stone", rate=500, min_quantity=1, max_quantity=1), Drop(code="sapphire", rate=4000, min_quantity=1, max_quantity=1), Drop(code="sapphire_stone", rate=500, min_quantity=1, max_quantity=1)]))
    death_knight: ContentMap = field(default_factory=lambda: ContentMap(name="Death Knight", code="death_knight", level=28, skill="combat", pos=Position(8, 7), drops=[Drop(code="death_knight_sword", rate=600, min_quantity=1, max_quantity=1), Drop(code="red_cloth", rate=12, min_quantity=1, max_quantity=1)]))
    lich: ContentMap = field(default_factory=lambda: ContentMap(name="Lich", code="lich", level=30, skill="combat", pos=Position(9, 7), drops=[Drop(code="life_crystal", rate=2000, min_quantity=1, max_quantity=1), Drop(code="lich_crown", rate=600, min_quantity=1, max_quantity=1)]))
    bat: ContentMap = field(default_factory=lambda: ContentMap(name="Bat", code="bat", level=38, skill="combat", pos=Position(8, 9), drops=[Drop(code="bat_wing", rate=12, min_quantity=1, max_quantity=1)]))
    glowstem: ContentMap = field(default_factory=lambda: ContentMap(name="Glowstem", code="glowstem", level=40, skill="alchemy", pos=Position(1, 10), drops=[Drop(code="glowstem_leaf", rate=1, min_quantity=1, max_quantity=1)]))  
    imp: ContentMap = field(default_factory=lambda: ContentMap(name="Imp", code="imp", level=28, skill="combat", pos=Position(0, 12), drops=[Drop(code="demoniac_dust", rate=12, min_quantity=1, max_quantity=1), Drop(code="piece_of_obsidian", rate=70, min_quantity=1, max_quantity=1)]))
    maple_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Maple Tree", code="maple_tree", level=40, skill="woodcutting", pos=Position(1, 12), drops=[Drop(code="maple_wood", rate=1, min_quantity=1, max_quantity=1), Drop(code="maple_sap", rate=10, min_quantity=1, max_quantity=1)]))
    bass_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Bass Fishing Spot", code="bass_fishing_spot", level=30, skill="fishing", pos=Position(6, 12), drops=[Drop(code="bass", rate=1, min_quantity=1, max_quantity=1), Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)]))
    trout_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Trout Fishing Spot", code="trout_fishing_spot", level=20, skill="fishing", pos=Position(7, 12), drops=[Drop(code="trout", rate=1, min_quantity=1, max_quantity=1), Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)]))
    mithril_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Mithril Rocks", code="mithril_rocks", level=40, skill="mining", pos=Position(-2, 13), drops=[Drop(code="mithril_ore", rate=1, min_quantity=1, max_quantity=1), Drop(code="topaz_stone", rate=550, min_quantity=1, max_quantity=1), Drop(code="topaz", rate=4500, min_quantity=1, max_quantity=1), Drop(code="emerald", rate=4500, min_quantity=1, max_quantity=1), Drop(code="emerald_stone", rate=550, min_quantity=1, max_quantity=1), Drop(code="ruby", rate=4500, min_quantity=1, max_quantity=1), Drop(code="ruby_stone", rate=550, min_quantity=1, max_quantity=1), Drop(code="sapphire", rate=4500, min_quantity=1, max_quantity=1), Drop(code="sapphire_stone", rate=550, min_quantity=1, max_quantity=1)]))
    hellhound: ContentMap = field(default_factory=lambda: ContentMap(name="Hellhound", code="hellhound", level=40, skill="combat", pos=Position(-1, 13), drops=[Drop(code="hellhound_hair", rate=12, min_quantity=1, max_quantity=1), Drop(code="raw_hellhound_meat", rate=10, min_quantity=1, max_quantity=1), Drop(code="hellhound_bone", rate=12, min_quantity=1, max_quantity=1)]))
    taskmaster_items: ContentMap = field(default_factory=lambda: ContentMap(name="Taksmaster of Items", code="items", level=1, skill=None, pos=Position(4, 13), drops=[]))
    nettle: ContentMap = field(default_factory=lambda: ContentMap(name="Nettle", code="nettle", level=20, skill="alchemy", pos=Position(7, 14), drops=[Drop(code="nettle_leaf", rate=1, min_quantity=1, max_quantity=1)]))       


@dataclass
class InventoryItem:
    """Represents an item in the player's inventory."""
    slot: int
    code: str
    quantity: int

    def __repr__(self) -> str:
        """String representation of the inventory item."""
        return f"({self.slot}) {self.quantity}x {self.code}"


@dataclass
class PlayerData:
    """
    Represents all data and stats related to a player.
    
    Attributes include levels, experience, stats, elemental attributes, 
    position, inventory, equipment slots, and task information.
    """
    name: str
    account: str
    skin: str
    level: int
    xp: int
    max_xp: int
    gold: int
    speed: int
    
    # Skill levels and XP
    mining_level: int
    mining_xp: int
    mining_max_xp: int
    woodcutting_level: int
    woodcutting_xp: int
    woodcutting_max_xp: int
    fishing_level: int
    fishing_xp: int
    fishing_max_xp: int
    weaponcrafting_level: int
    weaponcrafting_xp: int
    weaponcrafting_max_xp: int
    gearcrafting_level: int
    gearcrafting_xp: int
    gearcrafting_max_xp: int
    jewelrycrafting_level: int
    jewelrycrafting_xp: int
    jewelrycrafting_max_xp: int
    cooking_level: int
    cooking_xp: int
    cooking_max_xp: int
    alchemy_level: int
    alchemy_xp: int
    alchemy_max_xp: int

    # Stats
    hp: int
    max_hp: int
    haste: int
    critical_strike: int
    stamina: int
    
    # Elemental attributes
    attack_fire: int
    attack_earth: int
    attack_water: int
    attack_air: int
    dmg_fire: int
    dmg_earth: int
    dmg_water: int
    dmg_air: int
    res_fire: int
    res_earth: int
    res_water: int
    res_air: int
    
    # Position and state
    pos: Position
    cooldown: int
    cooldown_expiration: str
    
    # Equipment slots
    weapon_slot: str
    shield_slot: str
    helmet_slot: str
    body_armor_slot: str
    leg_armor_slot: str
    boots_slot: str
    ring1_slot: str
    ring2_slot: str
    amulet_slot: str
    artifact1_slot: str
    artifact2_slot: str
    artifact3_slot: str
    utility1_slot: str
    utility1_slot_quantity: int
    utility2_slot: str
    utility2_slot_quantity: int
    
    # Task information
    task: str
    task_type: str
    task_progress: int
    task_total: int
    
    # Inventory
    inventory_max_items: int
    inventory: List[InventoryItem]

    def get_skill_progress(self, skill: str) -> Tuple[int, float]:
        """
        Get level and progress percentage for a given skill.
        
        Args:
            skill (str): The skill name (e.g., 'mining', 'fishing').
        
        Returns:
            tuple: A tuple containing the level (int) and progress (float) in percentage.
        """
        level = getattr(self, f"{skill}_level")
        xp = getattr(self, f"{skill}_xp")
        max_xp = getattr(self, f"{skill}_max_xp")
        progress = (xp / max_xp) * 100 if max_xp > 0 else 0
        return level, progress

    def get_equipment_slots(self) -> Dict[str, str]:
        """
        Get all equipped items in each slot as a dictionary.
        
        Returns:
            dict: A dictionary mapping each slot name to the equipped item.
        """
        return {
            "weapon": self.weapon_slot,
            "shield": self.shield_slot,
            "helmet": self.helmet_slot,
            "body": self.body_armor_slot,
            "legs": self.leg_armor_slot,
            "boots": self.boots_slot,
            "ring1": self.ring1_slot,
            "ring2": self.ring2_slot,
            "amulet": self.amulet_slot,
            "artifact1": self.artifact1_slot,
            "artifact2": self.artifact2_slot,
            "artifact3": self.artifact3_slot,
            "utility1": self.utility1_slot,
            "utility2": self.utility2_slot
        }

    def get_inventory_space(self) -> int:
        """
        Calculate remaining inventory space.
        
        Returns:
            int: Number of available inventory slots.
        """
        items = 0
        for item in self.inventory:
            items += item.quantity
        return self.inventory_max_items - items

    def has_item(self, item_code: str) -> Tuple[bool, int]:
        """
        Check if the player has a specific item and its quantity.
        
        Args:
            item_code (str): The code of the item to check.
        
        Returns:
            tuple: A tuple with a boolean indicating presence and the quantity.
        """
        for item in self.inventory:
            if item.code == item_code:
                return True, item.quantity
        return False, 0

    def get_task_progress_percentage(self) -> float:
        """
        Get the current task progress as a percentage.
        
        Returns:
            float: The task completion percentage.
        """
        return (self.task_progress / self.task_total) * 100 if self.task_total > 0 else 0
    
    def __repr__(self) -> str:
        """String representation of player's core stats and skills."""
        ret = \
        f"""{self.name}
  Combat Level {self.level} ({self.xp}/{self.max_xp} XP)
  Mining Level {self.mining_level} ({self.mining_xp}/{self.mining_max_xp} XP)
  Woodcutting Level {self.woodcutting_level} ({self.woodcutting_xp}/{self.woodcutting_max_xp} XP)
  Fishing Level {self.fishing_level} ({self.fishing_xp}/{self.fishing_max_xp} XP)
  Weaponcrafting Level {self.weaponcrafting_level} ({self.weaponcrafting_xp}/{self.weaponcrafting_max_xp} XP)
  Gearcrafting Level {self.gearcrafting_level} ({self.gearcrafting_xp}/{self.gearcrafting_max_xp} XP)
  Jewelrycrafting Level {self.jewelrycrafting_level} ({self.jewelrycrafting_xp}/{self.jewelrycrafting_max_xp} XP)
  Cooking Level {self.cooking_level} ({self.cooking_xp}/{self.cooking_max_xp} XP)
        """
        return ret
# --- End Dataclasses ---


class Account:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Account Functions ---
    def get_bank_details(self) -> dict:
        """Retrieve the details of the player's bank account."""
        endpoint = "my/bank"
        return self.api._make_request("GET", endpoint, source="get_bank_details")

    def get_bank_items(self, item_code=None, page=1) -> dict:
        """Retrieve the list of items stored in the player's bank."""
        query = "size=100"
        query += f"&item_code={item_code}" if item_code else ""
        query += f"&page={page}"
        endpoint = f"my/bank/items?{query}"
        return self.api._make_request("GET", endpoint, source="get_bank_items")

    def get_ge_sell_orders(self, item_code=None, page=1) -> dict:
        """Retrieve the player's current sell orders on the Grand Exchange."""
        query = "size=100"
        query += f"&item_code={item_code}" if item_code else ""
        query += f"&page={page}"
        endpoint = f"my/grandexchange/orders?{query}"
        return self.api._make_request("GET", endpoint, source="get_ge_sell_orders")

    def get_ge_sell_history(self, item_code=None, item_id=None, page=1) -> dict:
        """Retrieve the player's Grand Exchange sell history."""
        query = "size=100"
        query += f"&item_code={item_code}" if item_code else ""
        query += f"&id={item_id}" if item_id else ""
        query += f"&page={page}"
        endpoint = f"my/grandexchange/history?{query}"
        return self.api._make_request("GET", endpoint, source="get_ge_sell_history")

    def get_account_details(self) -> dict:
        """Retrieve details of the player's account."""
        endpoint = "my/details"
        return self.api._make_request("GET", endpoint, source="get_account_details")

class Character:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Character Functions ---
    def create_character(self, name: str, skin: str = "men1") -> dict:
        """
        Create a new character with the given name and skin.

        Args:
            name (str): The name of the new character.
            skin (str): The skin choice for the character (default is "men1").

        Returns:
            dict: Response data with character creation details.
        """
        endpoint = "characters/create"
        json = {"name": name, "skin": skin}
        return self.api._make_request("POST", endpoint, json=json, source="create_character")

    def delete_character(self, name: str) -> dict:
        """
        Delete a character by name.

        Args:
            name (str): The name of the character to delete.

        Returns:
            dict: Response data confirming character deletion.
        """
        endpoint = "characters/delete"
        json = {"name": name}
        return self.api._make_request("POST", endpoint, json=json, source="delete_character")

    def get_logs(self, page: int = 1) -> dict:
        """_summary_

        Args:
            page (int): Page number for results. Defaults to 1.

        Returns:
            dict: Response data with character logs
        """
        query = f"size=100&page={page}"
        endpoint = f"my/logs?{query}"
        self.api._make_request("GET", endpoint, source="get_logs")

class Actions:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Character Actions ---
    def move(self, x: int, y: int) -> dict:
        """
        Move the character to a new position.

        Args:
            x (int): X-coordinate to move to.
            y (int): Y-coordinate to move to.

        Returns:
            dict: Response data with updated character position.
        """
        endpoint = f"my/{self.api.char.name}/action/move"
        json = {"x": x, "y": y}
        res = self.api._make_request("POST", endpoint, json=json, source="move")
        return res

    def rest(self) -> dict:
        """
        Perform a rest action to regain energy.

        Returns:
            dict: Response data confirming rest action.
        """
        endpoint = f"my/{self.api.char.name}/action/rest"
        res = self.api._make_request("POST", endpoint, source="rest")
        return res

    # --- Item Action Functions ---
    def equip_item(self, item_code: str, slot: str, quantity: int = 1) -> dict:
        """
        Equip an item to a specified slot.

        Args:
            item_code (str): The code of the item to equip.
            slot (str): The equipment slot.
            quantity (int): The number of items to equip (default is 1).

        Returns:
            dict: Response data with updated equipment.
        """
        endpoint = f"my/{self.api.char.name}/action/equip"
        json = {"code": item_code, "slot": slot, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="equip_item")
        return res

    def unequip_item(self, slot: str, quantity: int = 1) -> dict:
        """
        Unequip an item from a specified slot.

        Args:
            slot (str): The equipment slot.
            quantity (int): The number of items to unequip (default is 1).

        Returns:
            dict: Response data with updated equipment.
        """
        endpoint = f"my/{self.api.char.name}/action/unequip"
        json = {"slot": slot, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="unequip_item")
        return res

    def use_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Use an item from the player's inventory.

        Args:
            item_code (str): Code of the item to use.
            quantity (int): Quantity of the item to use (default is 1).

        Returns:
            dict: Response data confirming the item use.
        """
        endpoint = f"my/{self.api.char.name}/action/use"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="use_item")
        return res

    def delete_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Delete an item from the player's inventory.

        Args:
            item_code (str): Code of the item to delete.
            quantity (int): Quantity of the item to delete (default is 1).

        Returns:
            dict: Response data confirming the item deletion.
        """
        endpoint = f"my/{self.api.char.name}/action/delete-item"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="delete_item")
        return res

    # --- Resource Action Functions ---
    def fight(self) -> dict:
        """
        Initiate a fight with a monster.

        Returns:
            dict: Response data with fight details.
        """
        endpoint = f"my/{self.api.char.name}/action/fight"
        res = self.api._make_request("POST", endpoint, source="fight")
        return res

    def gather(self) -> dict:
        """
        Gather resources, such as mining, woodcutting, or fishing.

        Returns:
            dict: Response data with gathered resources.
        """
        endpoint = f"my/{self.api.char.name}/action/gathering"
        res = self.api._make_request("POST", endpoint, source="gather")
        return res

    def craft_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Craft an item.

        Args:
            item_code (str): Code of the item to craft.
            quantity (int): Quantity of the item to craft (default is 1).

        Returns:
            dict: Response data with crafted item details.
        """
        endpoint = f"my/{self.api.char.name}/action/crafting"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="craft_item")
        return res

    def recycle_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Recycle an item.

        Args:
            item_code (str): Code of the item to recycle.
            quantity (int): Quantity of the item to recycle (default is 1).

        Returns:
            dict: Response data confirming the recycling action.
        """
        endpoint = f"my/{self.api.char.name}/action/recycle"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="recycle_item")
        return res

    # --- Bank Action Functions ---
    def bank_deposit_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Deposit an item into the bank.

        Args:
            item_code (str): Code of the item to deposit.
            quantity (int): Quantity of the item to deposit (default is 1).

        Returns:
            dict: Response data confirming the deposit.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/deposit"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="bank_deposit_item")
        return res

    def bank_deposit_gold(self, quantity: int) -> dict:
        """
        Deposit gold into the bank.

        Args:
            quantity (int): Amount of gold to deposit.

        Returns:
            dict: Response data confirming the deposit.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/deposit/gold"
        json = {"quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="bank_deposit_gold")
        return res

    def bank_withdraw_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Withdraw an item from the bank.

        Args:
            item_code (str): Code of the item to withdraw.
            quantity (int): Quantity of the item to withdraw (default is 1).

        Returns:
            dict: Response data confirming the withdrawal.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/withdraw"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="bank_withdraw_item")
        return res

    def bank_withdraw_gold(self, quantity: int) -> dict:
        """
        Withdraw gold from the bank.

        Args:
            quantity (int): Amount of gold to withdraw.

        Returns:
            dict: Response data confirming the withdrawal.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/withdraw/gold"
        json = {"quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="bank_withdraw_gold")
        return res

    def bank_buy_expansion(self) -> dict:
        """
        Purchase an expansion for the bank.

        Returns:
            dict: Response data confirming the expansion purchase.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/buy_expansion"
        res = self.api._make_request("POST", endpoint, source="bank_buy_expansion")
        return res

    # --- Grand Exchange Actions Functions ---
    def ge_buy_item(self, order_id: str, quantity: int = 1) -> dict:
        """
        Buy an item from the Grand Exchange.

        Args:
            order_id (str): ID of the order to buy from.
            quantity (int): Quantity of the item to buy (default is 1).

        Returns:
            dict: Response data with transaction details.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/buy"
        json = {"id": order_id, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="ge_buy")
        return res

    def ge_create_sell_order(self, item_code: str, price: int, quantity: int = 1) -> dict:
        """
        Create a sell order on the Grand Exchange.

        Args:
            item_code (str): Code of the item to sell.
            price (int): Selling price per unit.
            quantity (int): Quantity of the item to sell (default is 1).

        Returns:
            dict: Response data confirming the sell order.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/sell"
        json = {"code": item_code, "item_code": price, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="ge_sell")
        return res

    def ge_cancel_sell_order(self, order_id: str) -> dict:
        """
        Cancel an active sell order on the Grand Exchange.

        Args:
            order_id (str): ID of the order to cancel.

        Returns:
            dict: Response data confirming the order cancellation.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/cancel"
        json = {"id": order_id}
        res = self.api._make_request("POST", endpoint, json=json, source="ge_cancel_sell")
        return res

    # --- Taskmaster Action Functions ---
    def taskmaster_accept_task(self) -> dict:
        """
        Accept a new task from the taskmaster.

        Returns:
            dict: Response data confirming task acceptance.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/new"
        res = self.api._make_request("POST", endpoint, source="accept_task")
        return res

    def taskmaster_complete_task(self) -> dict:
        """
        Complete the current task with the taskmaster.

        Returns:
            dict: Response data confirming task completion.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/complete"
        res = self.api._make_request("POST", endpoint, source="complete_task")
        return res

    def taskmaster_exchange_task(self) -> dict:
        """
        Exchange the current task with the taskmaster.

        Returns:
            dict: Response data confirming task exchange.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/exchange"
        res = self.api._make_request("POST", endpoint, source="exchange_task")
        return res

    def taskmaster_trade_task(self, item_code: str, quantity: int = 1) -> dict:
        """
        Trade a task item with another character.

        Args:
            item_code (str): Code of the item to trade.
            quantity (int): Quantity of the item to trade (default is 1).

        Returns:
            dict: Response data confirming task trade.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/trade"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json, source="trade_task")
        return res

    def taskmaster_cancel_task(self) -> dict:
        """
        Cancel the current task with the taskmaster.

        Returns:
            dict: Response data confirming task cancellation.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/cancel"
        res = self.api._make_request("POST", endpoint, source="cancel_task")
        return res
 
class Items:
    def __init__(self, api):
        self.api = api
        self.cache = {}
        self.all_items = []
    
    def _cache_items(self):
        endpoint = "items?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_items")
        pages = math.ceil(int(res["pages"]) / 100)
        
        m = f"Caching {pages} pages of items"
        logger.debug(m, extra={"char": self.api.char.name})
        
        all_items = []
        for i in range(pages):
            endpoint = f"items?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_items")
            item_list = res["data"]
            all_items.extend(item_list)
            
            # Log the number of items fetched in each page
            logger.debug(f"Fetched {len(item_list)} items from page {i+1}", extra={"char": self.api.char.name})
        
        self.cache = {item['code']: item for item in all_items}
        self.all_items = all_items
        
        logger.debug(f"Finished caching {len(all_items)} items", extra={"char": self.api.char.name})
    
    def _filter_items(self, params):
        # Initialize the filtered list with all items
        logger.debug(f"Filtering items with params: {params}", extra={"char": self.api.char.name})
        
        filtered_items = self.all_items
        
        or_conditions = {}
        for key, value in params.items():
            if key.startswith("~"):
                key = key[1:]
                if key not in or_conditions:
                    or_conditions[key] = []
                or_conditions[key].append(value)
                logger.debug(f"OR condition for {key}: {value}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
                
                if key == 'craft_material':
                    filtered_items = [item for item in filtered_items if item.get('craft') and any(material['code'] == value for material in item['craft'].get('items', []))]
                    logger.debug(f"Filtered by craft_material: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
                elif key == 'craft_skill':
                    filtered_items = [item for item in filtered_items if item.get('craft') and item['craft']['skill'] == value]
                    logger.debug(f"Filtered by craft_skill: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
                elif key == 'max_level':
                    filtered_items = [item for item in filtered_items if item['level'] <= value]
                    logger.debug(f"Filtered by max_level: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
                elif key == 'min_level':
                    filtered_items = [item for item in filtered_items if item['level'] >= value]
                    logger.debug(f"Filtered by min_level: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
                elif key == 'name':
                    name_pattern = re.compile(value, re.IGNORECASE)
                    filtered_items = [item for item in filtered_items if name_pattern.search(item['name'])]
                    logger.debug(f"Filtered by name: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
                elif key == 'item_type':
                    filtered_items = [item for item in filtered_items if item['type'] == value]
                    logger.debug(f"Filtered by item_type: {value}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})

        for key, values in or_conditions.items():
            filtered_items = [item for item in filtered_items if any(item.get(key) == v for v in values)]
            logger.debug(f"Applied OR condition for {key} with values: {values}. Remaining items: {len(filtered_items)}", extra={"char": self.api.char.name})
        
        logger.debug(f"Filtering complete. Total items after filtering: {len(filtered_items)}", extra={"char": self.api.char.name})
        return filtered_items

    def get_item(self, params):
        logger.debug(f"Getting item with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_items:
            logger.debug("Cache is empty, calling _cache_items() to load items.", extra={"char": self.api.char.name})
            self._cache_items()

        if "item_code" in params:
            item = self.cache.get(params["item_code"])
            if item:
                logger.debug(f"Found item with code {params['item_code']}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Item with code {params['item_code']} not found in cache", extra={"char": self.api.char.name})
            return item
        
        filtered_items = self._filter_items(params)
        logger.debug(f"Returning {len(filtered_items)} filtered items", extra={"char": self.api.char.name})
        return filtered_items

class Maps:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_maps = []

    def _cache_maps(self):
        endpoint = "maps?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_maps")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of maps", extra={"char": self.api.char.name})
        
        all_maps = []
        for i in range(pages):
            endpoint = f"maps?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_maps")
            map_list = res["data"]
            all_maps.extend(map_list)
            logger.debug(f"Fetched {len(map_list)} maps from page {i+1}", extra={"char": self.api.char.name})
        
        self.cache = {f"{item['x']}/{item['y']}": item for item in all_maps}
        self.all_maps = all_maps
        
        logger.debug(f"Finished caching {len(all_maps)} maps", extra={"char": self.api.char.name})

    def _filter_maps(self, params):
        logger.debug(f"Filtering maps with params: {params}", extra={"char": self.api.char.name})
        
        filtered_maps = self.all_maps
        
        for key, value in params.items():
            logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
            
            if key == 'map_content':
                content_pattern = re.compile(value, re.IGNORECASE)
                filtered_maps = [map_item for map_item in filtered_maps if content_pattern.search(map_item.get('content', ''))]
            elif key == 'content_type':
                filtered_maps = [map_item for map_item in filtered_maps if map_item.get('content_type') == value]

        logger.debug(f"Filtering complete. Total maps after filtering: {len(filtered_maps)}", extra={"char": self.api.char.name})
        return filtered_maps

    def get_map(self, params):
        logger.debug(f"Getting map with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_maps:
            logger.debug("Cache is empty, calling _cache_maps() to load maps.", extra={"char": self.api.char.name})
            self._cache_maps()

        if "x" in params and "y" in params:
            map_key = f"{params['x']}/{params['y']}"
            map_item = self.cache.get(map_key)
            if map_item:
                logger.debug(f"Found map at coordinates {map_key}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Map at coordinates {map_key} not found in cache", extra={"char": self.api.char.name})
            return map_item
        
        filtered_maps = self._filter_maps(params)
        logger.debug(f"Returning {len(filtered_maps)} filtered maps", extra={"char": self.api.char.name})
        return filtered_maps

class Monsters:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_monsters = []

    def _cache_monsters(self):
        endpoint = "monsters?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_monsters")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of monsters", extra={"char": self.api.char.name})
        
        all_monsters = []
        for i in range(pages):
            endpoint = f"monsters?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_monsters")
            monster_list = res["data"]
            all_monsters.extend(monster_list)
            logger.debug(f"Fetched {len(monster_list)} monsters from page {i+1}", extra={"char": self.api.char.name})
        
        self.cache = {monster['code']: monster for monster in all_monsters}
        self.all_monsters = all_monsters
        
        logger.debug(f"Finished caching {len(all_monsters)} monsters", extra={"char": self.api.char.name})

    def _filter_monsters(self, params):
        logger.debug(f"Filtering monsters with params: {params}", extra={"char": self.api.char.name})
        
        filtered_monsters = self.all_monsters
        
        for key, value in params.items():
            logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
            
            if key == 'drop':
                filtered_monsters = [monster for monster in filtered_monsters 
                                  if any(drop['code'] == value for drop in monster.get('drops', []))]
            elif key == 'max_level':
                filtered_monsters = [monster for monster in filtered_monsters if monster['level'] <= value]
            elif key == 'min_level':
                filtered_monsters = [monster for monster in filtered_monsters if monster['level'] >= value]

        logger.debug(f"Filtering complete. Total monsters after filtering: {len(filtered_monsters)}", 
                    extra={"char": self.api.char.name})
        return filtered_monsters

    def get_monster(self, params):
        logger.debug(f"Getting monster with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_monsters:
            logger.debug("Cache is empty, calling _cache_monsters() to load monsters.", 
                        extra={"char": self.api.char.name})
            self._cache_monsters()

        if "monster_code" in params:
            monster = self.cache.get(params["monster_code"])
            if monster:
                logger.debug(f"Found monster with code {params['monster_code']}", 
                            extra={"char": self.api.char.name})
            else:
                logger.debug(f"Monster with code {params['monster_code']} not found in cache", 
                            extra={"char": self.api.char.name})
            return monster
        
        filtered_monsters = self._filter_monsters(params)
        logger.debug(f"Returning {len(filtered_monsters)} filtered monsters", 
                    extra={"char": self.api.char.name})
        return filtered_monsters

class Resources:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_resources = []

    def _cache_resources(self):
        endpoint = "resources?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_resources")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of resources", extra={"char": self.api.char.name})
        
        all_resources = []
        for i in range(pages):
            endpoint = f"resources?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_resources")
            resource_list = res["data"]
            all_resources.extend(resource_list)
            logger.debug(f"Fetched {len(resource_list)} resources from page {i+1}", 
                        extra={"char": self.api.char.name})
        
        self.cache = {resource['code']: resource for resource in all_resources}
        self.all_resources = all_resources
        
        logger.debug(f"Finished caching {len(all_resources)} resources", extra={"char": self.api.char.name})

    def _filter_resources(self, params):
        logger.debug(f"Filtering resources with params: {params}", extra={"char": self.api.char.name})
        
        filtered_resources = self.all_resources
        
        for key, value in params.items():
            logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
            
            if key == 'drop':
                filtered_resources = [resource for resource in filtered_resources 
                                   if any(drop['code'] == value for drop in resource.get('drops', []))]
            elif key == 'max_level':
                filtered_resources = [resource for resource in filtered_resources if resource['level'] <= value]
            elif key == 'min_level':
                filtered_resources = [resource for resource in filtered_resources if resource['level'] >= value]
            elif key == 'skill':
                filtered_resources = [resource for resource in filtered_resources if resource.get('skill') == value]

        logger.debug(f"Filtering complete. Total resources after filtering: {len(filtered_resources)}", 
                    extra={"char": self.api.char.name})
        return filtered_resources

    def get_resource(self, params):
        logger.debug(f"Getting resource with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_resources:
            logger.debug("Cache is empty, calling _cache_resources() to load resources.", 
                        extra={"char": self.api.char.name})
            self._cache_resources()

        if "resource_code" in params:
            resource = self.cache.get(params["resource_code"])
            if resource:
                logger.debug(f"Found resource with code {params['resource_code']}", 
                            extra={"char": self.api.char.name})
            else:
                logger.debug(f"Resource with code {params['resource_code']} not found in cache", 
                            extra={"char": self.api.char.name})
            return resource
        
        filtered_resources = self._filter_resources(params)
        logger.debug(f"Returning {len(filtered_resources)} filtered resources", 
                    extra={"char": self.api.char.name})
        return filtered_resources

class Tasks:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_tasks = []
        self.rewards_cache = {}
        self.all_rewards = []

    def _cache_tasks(self):
        endpoint = "tasks/list?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_tasks")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of tasks", extra={"char": self.api.char.name})
        
        all_tasks = []
        for i in range(pages):
            endpoint = f"tasks/list?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_tasks")
            task_list = res["data"]
            all_tasks.extend(task_list)
            logger.debug(f"Fetched {len(task_list)} tasks from page {i+1}", extra={"char": self.api.char.name})
        
        self.cache = {task['code']: task for task in all_tasks}
        self.all_tasks = all_tasks
        
        logger.debug(f"Finished caching {len(all_tasks)} tasks", extra={"char": self.api.char.name})

    def _cache_rewards(self):
        endpoint = "tasks/rewards?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_task_rewards")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of task rewards", extra={"char": self.api.char.name})
        
        all_rewards = []
        for i in range(pages):
            endpoint = f"tasks/rewards?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_task_rewards")
            reward_list = res["data"]
            all_rewards.extend(reward_list)
            logger.debug(f"Fetched {len(reward_list)} task rewards from page {i+1}", extra={"char": self.api.char.name})
        
        self.rewards_cache = {reward['code']: reward for reward in all_rewards}
        self.all_rewards = all_rewards
        
        logger.debug(f"Finished caching {len(all_rewards)} task rewards", extra={"char": self.api.char.name})

    def _filter_tasks(self, params):
        logger.debug(f"Filtering tasks with params: {params}", extra={"char": self.api.char.name})
        
        filtered_tasks = self.all_tasks
        
        or_conditions = {}
        for key, value in params.items():
            if key.startswith("~"):
                key = key[1:]
                if key not in or_conditions:
                    or_conditions[key] = []
                or_conditions[key].append(value)
                logger.debug(f"OR condition for {key}: {value}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
                
                if key == 'skill':
                    filtered_tasks = [task for task in filtered_tasks if task.get('skill') == value]
                elif key == 'task_type':
                    filtered_tasks = [task for task in filtered_tasks if task.get('type') == value]
                elif key == 'max_level':
                    filtered_tasks = [task for task in filtered_tasks if task['level'] <= value]
                elif key == 'min_level':
                    filtered_tasks = [task for task in filtered_tasks if task['level'] >= value]
                elif key == 'name':
                    name_pattern = re.compile(value, re.IGNORECASE)
                    filtered_tasks = [task for task in filtered_tasks if name_pattern.search(task['name'])]

        # Apply OR conditions
        for key, values in or_conditions.items():
            filtered_tasks = [task for task in filtered_tasks if any(task.get(key) == v for v in values)]
            logger.debug(f"Applied OR condition for {key} with values: {values}. Remaining tasks: {len(filtered_tasks)}", 
                        extra={"char": self.api.char.name})

        logger.debug(f"Filtering complete. Total tasks after filtering: {len(filtered_tasks)}", 
                    extra={"char": self.api.char.name})
        return filtered_tasks

    def _filter_rewards(self, params):
        logger.debug(f"Filtering task rewards with params: {params}", extra={"char": self.api.char.name})
        
        filtered_rewards = self.all_rewards
        
        or_conditions = {}
        for key, value in params.items():
            if key.startswith("~"):
                key = key[1:]
                if key not in or_conditions:
                    or_conditions[key] = []
                or_conditions[key].append(value)
                logger.debug(f"OR condition for {key}: {value}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
                
                if key == 'name':
                    name_pattern = re.compile(value, re.IGNORECASE)
                    filtered_rewards = [reward for reward in filtered_rewards if name_pattern.search(reward['name'])]

        # Apply OR conditions
        for key, values in or_conditions.items():
            filtered_rewards = [reward for reward in filtered_rewards if any(reward.get(key) == v for v in values)]
            logger.debug(f"Applied OR condition for {key} with values: {values}. Remaining rewards: {len(filtered_rewards)}", 
                        extra={"char": self.api.char.name})

        logger.debug(f"Filtering complete. Total rewards after filtering: {len(filtered_rewards)}", 
                    extra={"char": self.api.char.name})
        return filtered_rewards

    def get_task(self, params):
        logger.debug(f"Getting task with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_tasks:
            logger.debug("Cache is empty, calling _cache_tasks() to load tasks.", 
                        extra={"char": self.api.char.name})
            self._cache_tasks()

        if "task_code" in params:
            task = self.cache.get(params["task_code"])
            if task:
                logger.debug(f"Found task with code {params['task_code']}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Task with code {params['task_code']} not found in cache", 
                            extra={"char": self.api.char.name})
            return task
        
        filtered_tasks = self._filter_tasks(params)
        logger.debug(f"Returning {len(filtered_tasks)} filtered tasks", extra={"char": self.api.char.name})
        return filtered_tasks

    def get_all_rewards(self, params=None):
        logger.debug(f"Getting all task rewards with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_rewards:
            logger.debug("Rewards cache is empty, calling _cache_rewards() to load rewards.", 
                        extra={"char": self.api.char.name})
            self._cache_rewards()

        if not params:
            return self.all_rewards

        filtered_rewards = self._filter_rewards(params)
        logger.debug(f"Returning {len(filtered_rewards)} filtered rewards", extra={"char": self.api.char.name})
        return filtered_rewards

    def get_reward(self, params):
        logger.debug(f"Getting task reward with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_rewards:
            logger.debug("Rewards cache is empty, calling _cache_rewards() to load rewards.", 
                        extra={"char": self.api.char.name})
            self._cache_rewards()

        if "task_code" in params:
            reward = self.rewards_cache.get(params["task_code"])
            if reward:
                logger.debug(f"Found reward with code {params['task_code']}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Reward with code {params['task_code']} not found in cache", 
                            extra={"char": self.api.char.name})
            return reward
        
        filtered_rewards = self._filter_rewards(params)
        logger.debug(f"Returning {len(filtered_rewards)} filtered rewards", extra={"char": self.api.char.name})
        return filtered_rewards
    
class Achievements:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_achievements = []

    def _cache_achievements(self):
        endpoint = "achievements?size=1"
        res = self.api._make_request("GET", endpoint, source="get_all_achievements")
        pages = math.ceil(int(res["pages"]) / 100)
        
        logger.debug(f"Caching {pages} pages of achievements", extra={"char": self.api.char.name})
        
        all_achievements = []
        for i in range(pages):
            endpoint = f"achievements?size=100&page={i+1}"
            res = self.api._make_request("GET", endpoint, source="get_all_achievements")
            achievement_list = res["data"]
            all_achievements.extend(achievement_list)
            logger.debug(f"Fetched {len(achievement_list)} achievements from page {i+1}", 
                        extra={"char": self.api.char.name})
        
        self.cache = {achievement['code']: achievement for achievement in all_achievements}
        self.all_achievements = all_achievements
        
        logger.debug(f"Finished caching {len(all_achievements)} achievements", 
                    extra={"char": self.api.char.name})

    def _filter_achievements(self, params):
        logger.debug(f"Filtering achievements with params: {params}", extra={"char": self.api.char.name})
        
        filtered_achievements = self.all_achievements
        
        or_conditions = {}
        for key, value in params.items():
            if key.startswith("~"):
                key = key[1:]
                if key not in or_conditions:
                    or_conditions[key] = []
                or_conditions[key].append(value)
                logger.debug(f"OR condition for {key}: {value}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Applying filter for {key}: {value}", extra={"char": self.api.char.name})
                
                if key == 'achievement_type':
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if achievement.get('type') == value]
                elif key == 'name':
                    name_pattern = re.compile(value, re.IGNORECASE)
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if name_pattern.search(achievement['name'])]
                elif key == 'description':
                    desc_pattern = re.compile(value, re.IGNORECASE)
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if desc_pattern.search(achievement.get('description', ''))]
                elif key == 'reward_type':
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if any(reward.get('type') == value 
                                                for reward in achievement.get('rewards', []))]
                elif key == 'reward_item':
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if any(reward.get('code') == value 
                                                for reward in achievement.get('rewards', []))]
                elif key == 'points_min':
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if achievement.get('points', 0) >= value]
                elif key == 'points_max':
                    filtered_achievements = [achievement for achievement in filtered_achievements 
                                          if achievement.get('points', 0) <= value]

        # Apply OR conditions
        for key, values in or_conditions.items():
            filtered_achievements = [achievement for achievement in filtered_achievements 
                                  if any(achievement.get(key) == v for v in values)]
            logger.debug(f"Applied OR condition for {key} with values: {values}. " + 
                        f"Remaining achievements: {len(filtered_achievements)}", 
                        extra={"char": self.api.char.name})

        logger.debug(f"Filtering complete. Total achievements after filtering: {len(filtered_achievements)}", 
                    extra={"char": self.api.char.name})
        return filtered_achievements

    def get_achievement(self, params):
        logger.debug(f"Getting achievement with params: {params}", extra={"char": self.api.char.name})
        
        if not self.all_achievements:
            logger.debug("Cache is empty, calling _cache_achievements() to load achievements.", 
                        extra={"char": self.api.char.name})
            self._cache_achievements()

        if "achievement_code" in params:
            achievement = self.cache.get(params["achievement_code"])
            if achievement:
                logger.debug(f"Found achievement with code {params['achievement_code']}", 
                            extra={"char": self.api.char.name})
            else:
                logger.debug(f"Achievement with code {params['achievement_code']} not found in cache", 
                            extra={"char": self.api.char.name})
            return achievement
        
        filtered_achievements = self._filter_achievements(params)
        logger.debug(f"Returning {len(filtered_achievements)} filtered achievements", 
                    extra={"char": self.api.char.name})
        return filtered_achievements

    def get_all(self, params=None):
        """
        Get all achievements with optional filtering.
        
        Args:
            params (dict, optional): Dictionary of filter parameters. Supported filters:
                - achievement_type: Filter by achievement type
                - name: Search achievement names (case-insensitive)
                - description: Search achievement descriptions (case-insensitive)
                - reward_type: Filter by type of reward
                - reward_item: Filter by specific reward item code
                - points_min: Filter by minimum points
                - points_max: Filter by maximum points
                Use '~' prefix for OR conditions (e.g. ~type: ['daily', 'weekly'])
        
        Returns:
            list: List of filtered achievements
        """
        if not self.all_achievements:
            self._cache_achievements()
            
        if not params:
            return self.all_achievements
            
        return self._filter_achievements(params)
    
class Events:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Event Functions ---
    def get_active(self, page: int = 1) -> dict:
        """
        Retrieve a list of active events.

        Args:
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of active events.
        """
        query = f"size=100&page={page}"
        endpoint = f"events/active?{query}"
        return self.api._make_request("GET", endpoint, source="get_active_events").get("data")

    def get_all(self, page: int = 1) -> dict:
        """
        Retrieve a list of all events.

        Args:
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of events.
        """
        query = f"size=100&page={page}"
        endpoint = f"events?{query}"
        return self.api._make_request("GET", endpoint, source="get_all_events").get("data")

class GE:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Grand Exchange Functions ---
    def get_history(self, item_code: str, buyer: Optional[str] = None, seller: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the transaction history for a specific item on the Grand Exchange.

        Args:
            item_code (str): Code of the item.
            buyer (Optional[str]): Filter history by buyer name.
            seller (Optional[str]): Filter history by seller name.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the item transaction history.
        """
        query = f"size=100&page={page}"
        if buyer:
            query += f"&buyer={buyer}"
        if seller:
            query += f"&seller={seller}"
        endpoint = f"grandexchange/history/{item_code}?{query}"
        return self.api._make_request("GET", endpoint, source="get_ge_history").get("data")

    def get_sell_orders(self, item_code: Optional[str] = None, seller: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of sell orders on the Grand Exchange with optional filters.

        Args:
            item_code (Optional[str]): Filter by item code.
            seller (Optional[str]): Filter by seller name.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of sell orders.
        """
        query = f"size=100&page={page}"
        if item_code:
            query += f"&item_code={item_code}"
        if seller:
            query += f"&seller={seller}"
        endpoint = f"grandexchange/orders?{query}"
        return self.api._make_request("GET", endpoint, source="get_ge_sell_orders").get("data")

    def get_sell_order(self, order_id: str) -> dict:
        """
        Retrieve details for a specific sell order on the Grand Exchange.

        Args:
            order_id (str): ID of the order.

        Returns:
            dict: Response data for the specified sell order.
        """
        endpoint = f"grandexchange/orders/{order_id}"
        return self.api._make_request("GET", endpoint, source="get_ge_sell_order").get("data")

class Leaderboard:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Leaderboard Functions ---
    def get_characters_leaderboard(self, sort: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the characters leaderboard with optional sorting.

        Args:
            sort (Optional[str]): Sorting criteria (e.g., 'level', 'xp').
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the characters leaderboard.
        """
        query = "size=100"
        if sort:
            query += f"&sort={sort}"
        query += f"&page={page}"
        endpoint = f"leaderboard/characters?{query}"
        return self.api._make_request("GET", endpoint, source="get_characters_leaderboard")

    def get_accounts_leaderboard(self, sort: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the accounts leaderboard with optional sorting.

        Args:
            sort (Optional[str]): Sorting criteria (e.g., 'points').
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the accounts leaderboard.
        """
        query = "size=100"
        if sort:
            query += f"&sort={sort}"
        query += f"&page={page}"
        endpoint = f"leaderboard/accounts?{query}"
        return self.api._make_request("GET", endpoint, source="get_accounts_leaderboard")

class Accounts:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Args:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Accounts Functions ---
    def get_account_achievements(self, account: str, completed: Optional[bool] = None, achievement_type: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of achievements for a specific account with optional filters.

        Args:
            account (str): Account name.
            completed (Optional[bool]): Filter by completion status (True for completed, False for not).
            achievement_type (Optional[str]): Filter achievements by type.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of achievements for the account.
        """
        query = "size=100"
        if completed is not None:
            query += f"&completed={str(completed).lower()}"
        if achievement_type:
            query += f"&achievement_type={achievement_type}"
        query += f"&page={page}"
        endpoint = f"/accounts/{account}/achievements?{query}"
        return self.api._make_request("GET", endpoint, source="get_account_achievements") 


    def get_account(self, account: str):
        endpoint = f"/acounts/{account}"
        return self.api._make_request("GET", endpoint, source="get_account")

# --- Wrapper ---
class ArtifactsAPI:
    def __init__(self, api_key: str, character_name: str):
        extra = {"char": character_name}
        self.logger = logging.LoggerAdapter(logger, extra)

        self.logger.debug("Instantiating wrapper for " + character_name, extra = {"char": character_name})

        self.token: str = api_key
        self.base_url: str = "https://api.artifactsmmo.com"
        self.headers: Dict[str, str] = {
            "content-type": "application/json",
            "Accept": "application/json",
            "Authorization": f'Bearer {self.token}'
        }
        
        # Initialize cooldown manager
        self._cooldown_manager = CooldownManager()
        self._cooldown_manager.logger = self.logger
        
        self.character_name = character_name
        self.char: PlayerData = self.get_character(character_name=character_name)

        # --- Subclass definition ---
        self.account = Account(self)
        self.character = Character(self)
        self.actions = Actions(self)
        self.maps = Maps(self)
        self.items = Items(self)
        self.monsters = Monsters(self)
        self.resources = Resources(self)
        self.events = Events(self)
        self.ge = GE(self)
        self.tasks = Tasks(self)
        self.achiecements = Achievements(self)
        self.leaderboard = Leaderboard(self)
        self.accounts = Accounts(self)
        self.content_maps = ContentMaps()

        self.logger.debug("Finished instantiating wrapper for " + character_name, extra = {"char": character_name})

    @with_cooldown
    def _make_request(self, method: str, endpoint: str, json: Optional[dict] = None, 
                     source: Optional[str] = None, retries: int = 3) -> dict:
        """
        Makes an API request and returns the JSON response.
        Now managed by cooldown decorator.
        """
        try:
            endpoint = endpoint.strip("/")
            url = f"{self.base_url}/{endpoint}"
            if source != "get_character":
                self.logger.debug(f"Sending API request to {url} with the following json:\n{json}", extra={"char": self.character_name})
            response = requests.request(method, url, headers=self.headers, json=json)

            if response.status_code != 200:
                message = f"An error occurred. Returned code {response.status_code}, {response.json().get('error', {}).get('message', '')} Endpoint: {endpoint}"
                message += f", Body: {json}" if json else ""
                message += f", Source: {source}" if source else ""

                self._raise(response.status_code, message)

            if source != "get_character":
                self.get_character()
                
            return response.json()

        except Exception as e:
            logger.error(e, extra={"char": self.character_name})
            if retries:
                retries -= 1
                logger.warning(f"Retrying, {retries} retries left", extra={"char": self.character_name})
                return self._make_request(method, endpoint, json, source, retries)


    def _raise(self, code: int, m: str) -> None:
        """
        Raises an API exception based on the response code and error message.

        Args:
            code (int): HTTP status code.
            m (str): Error message.

        Raises:
            Exception: Corresponding exception based on the code provided.
        """
        match code:
            case 404:
                raise APIException.NotFound(m)
            case 478:
                raise APIException.InsufficientQuantity(m)
            case 486:
                raise APIException.ActionAlreadyInProgress(m)
            case 493:
                raise APIException.TooLowLevel(m)
            case 496:
                raise APIException.TooLowLevel(m)
            case 497:
                raise APIException.InventoryFull(m)
            case 498:
                raise APIException.CharacterNotFound(m)
            case 499:
                raise APIException.CharacterInCooldown(m)
            case 497:
                raise APIException.GETooMany(m)
            case 480:
                raise APIException.GENoStock(m)
            case 482:
                raise APIException.GENoItem(m)
            case 483:
                raise APIException.TransactionInProgress(m)
            case 486:
                raise APIException.InsufficientGold(m)
            case 461:
                raise APIException.TransactionInProgress(m)
            case 462:
                raise APIException.BankFull(m)
            case 489:
                raise APIException.TaskMasterAlreadyHasTask(m)
            case 487:
                raise APIException.TaskMasterNoTask(m)
            case 488:
                raise APIException.TaskMasterTaskNotComplete(m)
            case 474:
                raise APIException.TaskMasterTaskMissing(m)
            case 475:
                raise APIException.TaskMasterTaskAlreadyCompleted(m)
            case 473:
                raise APIException.RecyclingItemNotRecyclable(m)
            case 484:
                raise APIException.EquipmentTooMany(m)
            case 485:
                raise APIException.EquipmentAlreadyEquipped(m)
            case 491:
                raise APIException.EquipmentSlot(m)
            case 490:
                logger.warning(m, extra={"char": self.char.name})
            case 452:
                raise APIException.TokenMissingorEmpty(m)
        if code != 200 and code != 490:
            raise Exception(m)


    # --- Helper Functions ---
    def get_character(self, data: Optional[dict] = None, character_name: Optional[str] = None) -> PlayerData:
        """
        Retrieve or update the character's data and initialize the character attribute.

        Args:
            data (Optional[dict]): Pre-loaded character data; if None, data will be fetched.
            character_name (Optional[str]): Name of the character; only used if data is None.

        Returns:
            PlayerData: The PlayerData object with the character's information.
        """
        if data is None:
            if character_name:
                endpoint = f"characters/{character_name}"
            else:
                endpoint = f"characters/{self.char.name}"
            data = self._make_request("GET", endpoint, source="get_character").get('data')

        inventory_data = data.get("inventory", [])
        player_inventory: List[InventoryItem] = [
            InventoryItem(slot=item["slot"], code=item["code"], quantity=item["quantity"]) 
            for item in inventory_data if item["code"]
        ]

        self.char = PlayerData(
            name=data["name"],
            account=data["account"],
            skin=data["skin"],
            level=data["level"],
            xp=data["xp"],
            max_xp=data["max_xp"],
            gold=data["gold"],
            speed=data["speed"],
            mining_level=data["mining_level"],
            mining_xp=data["mining_xp"],
            mining_max_xp=data["mining_max_xp"],
            woodcutting_level=data["woodcutting_level"],
            woodcutting_xp=data["woodcutting_xp"],
            woodcutting_max_xp=data["woodcutting_max_xp"],
            fishing_level=data["fishing_level"],
            fishing_xp=data["fishing_xp"],
            fishing_max_xp=data["fishing_max_xp"],
            weaponcrafting_level=data["weaponcrafting_level"],
            weaponcrafting_xp=data["weaponcrafting_xp"],
            weaponcrafting_max_xp=data["weaponcrafting_max_xp"],
            gearcrafting_level=data["gearcrafting_level"],
            gearcrafting_xp=data["gearcrafting_xp"],
            gearcrafting_max_xp=data["gearcrafting_max_xp"],
            jewelrycrafting_level=data["jewelrycrafting_level"],
            jewelrycrafting_xp=data["jewelrycrafting_xp"],
            jewelrycrafting_max_xp=data["jewelrycrafting_max_xp"],
            cooking_level=data["cooking_level"],
            cooking_xp=data["cooking_xp"],
            cooking_max_xp=data["cooking_max_xp"],
            alchemy_level=data["alchemy_level"],
            alchemy_xp=data["alchemy_xp"],
            alchemy_max_xp=data["alchemy_max_xp"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            haste=data["haste"],
            critical_strike=data["critical_strike"],
            stamina=data["stamina"],
            attack_fire=data["attack_fire"],
            attack_earth=data["attack_earth"],
            attack_water=data["attack_water"],
            attack_air=data["attack_air"],
            dmg_fire=data["dmg_fire"],
            dmg_earth=data["dmg_earth"],
            dmg_water=data["dmg_water"],
            dmg_air=data["dmg_air"],
            res_fire=data["res_fire"],
            res_earth=data["res_earth"],
            res_water=data["res_water"],
            res_air=data["res_air"],
            pos=Position(data["x"], data["y"]),
            cooldown=data["cooldown"],
            cooldown_expiration=data["cooldown_expiration"],
            weapon_slot=data["weapon_slot"],
            shield_slot=data["shield_slot"],
            helmet_slot=data["helmet_slot"],
            body_armor_slot=data["body_armor_slot"],
            leg_armor_slot=data["leg_armor_slot"],
            boots_slot=data["boots_slot"],
            ring1_slot=data["ring1_slot"],
            ring2_slot=data["ring2_slot"],
            amulet_slot=data["amulet_slot"],
            artifact1_slot=data["artifact1_slot"],
            artifact2_slot=data["artifact2_slot"],
            artifact3_slot=data["artifact3_slot"],
            utility1_slot=data["utility1_slot"],
            utility2_slot=data["utility2_slot"],
            utility1_slot_quantity=data["utility1_slot_quantity"],
            utility2_slot_quantity=data["utility2_slot_quantity"],
            task=data["task"],
            task_type=data["task_type"],
            task_progress=data["task_progress"],
            task_total=data["task_total"],
            inventory_max_items=data["inventory_max_items"],
            inventory=player_inventory
        )
        return self.char
    
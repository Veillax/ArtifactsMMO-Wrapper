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
import sqlite3
import json

logger = logging.getLogger(__name__)

# Define the logging format you want to apply
formatter = logging.Formatter(
    fmt="\33[34m[%(levelname)s] %(asctime)s - %(char)s:\33[0m %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Create a handler (e.g., StreamHandler for console output) and set its format
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

# --- Globals ---
db = sqlite3.connect('artifacts.db')
db_cursor = db.cursor()
db_cursor.execute("CREATE TABLE IF NOT EXISTS cache_table (cache_table TEXT PRIMARY KEY, version TEXT)")
db.commit()

# --- Helpers ---
def _re_cache(api, table):
    print(table)
    
    # Use parameterized query to avoid SQL injection
    db_cursor.execute("SELECT version FROM cache_table WHERE cache_table = ?", (table,))
    version = db_cursor.fetchone()

    app_version = api._get_version()

    try:
        if version:
            if app_version != version[0]:
                db_cursor.execute("INSERT or REPLACE INTO cache_table (cache_table, version) VALUES (?, ?)", (table, app_version))
                db.commit()
                return True

        else:  # No record exists
            db_cursor.execute("INSERT or REPLACE INTO cache_table (cache_table, version) VALUES (?, ?)", (table, app_version))
            db.commit()
            return True

        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

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
            self.cooldown_expiration_time = datetime.fromisoformat(expiration_time_str.replace("Z", "+00:00"))

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


# --- Exceptions ---
class APIException(Exception):
    """Base exception class for API errors"""
    
    # Log the exception when it is raised
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"APIException raised: {message}", extra={"char": "ROOT"})

    class CharacterInCooldown(Exception):
        def __init__(self, message="Character is in cooldown"):
            super().__init__(message)
            logger.warning(f"CharacterInCooldown: {message}", extra={"char": "ROOT"})

    class NotFound(Exception):
        def __init__(self, message="Resource not found"):
            super().__init__(message)
            logger.error(f"NotFound: {message}", extra={"char": "ROOT"})

    class ActionAlreadyInProgress(Exception):
        def __init__(self, message="Action is already in progress"):
            super().__init__(message)
            logger.warning(f"ActionAlreadyInProgress: {message}", extra={"char": "ROOT"})

    class CharacterNotFound(Exception):
        def __init__(self, message="Character not found"):
            super().__init__(message)
            logger.error(f"CharacterNotFound: {message}", extra={"char": "ROOT"})

    class TooLowLevel(Exception):
        def __init__(self, message="Level is too low"):
            super().__init__(message)
            logger.error(f"TooLowLevel: {message}", extra={"char": "ROOT"})

    class InventoryFull(Exception):
        def __init__(self, message="Inventory is full"):
            super().__init__(message)
            logger.warning(f"InventoryFull: {message}", extra={"char": "ROOT"})

    class MapItemNotFound(Exception):
        def __init__(self, message="Map item not found"):
            super().__init__(message)
            logger.error(f"MapItemNotFound: {message}", extra={"char": "ROOT"})

    class InsufficientQuantity(Exception):
        def __init__(self, message="Insufficient quantity"):
            super().__init__(message)
            logger.warning(f"InsufficientQuantity: {message}", extra={"char": "ROOT"})

    class GETooMany(Exception):
        def __init__(self, message="Too many GE items"):
            super().__init__(message)
            logger.error(f"GETooMany: {message}", extra={"char": "ROOT"})

    class GENoStock(Exception):
        def __init__(self, message="No stock available"):
            super().__init__(message)
            logger.error(f"GENoStock: {message}", extra={"char": "ROOT"})

    class GENoItem(Exception):
        def __init__(self, message="Item not found in GE"):
            super().__init__(message)
            logger.error(f"GENoItem: {message}", extra={"char": "ROOT"})

    class TransactionInProgress(Exception):
        def __init__(self, message="Transaction already in progress"):
            super().__init__(message)
            logger.warning(f"TransactionInProgress: {message}", extra={"char": "ROOT"})

    class InsufficientGold(Exception):
        def __init__(self, message="Not enough gold"):
            super().__init__(message)
            logger.warning(f"InsufficientGold: {message}", extra={"char": "ROOT"})

    class TaskMasterNoTask(Exception):
        def __init__(self, message="No task assigned to TaskMaster"):
            super().__init__(message)
            logger.error(f"TaskMasterNoTask: {message}", extra={"char": "ROOT"})

    class TaskMasterAlreadyHasTask(Exception):
        def __init__(self, message="TaskMaster already has a task"):
            super().__init__(message)
            logger.warning(f"TaskMasterAlreadyHasTask: {message}", extra={"char": "ROOT"})

    class TaskMasterTaskNotComplete(Exception):
        def __init__(self, message="TaskMaster task is not complete"):
            super().__init__(message)
            logger.error(f"TaskMasterTaskNotComplete: {message}", extra={"char": "ROOT"})

    class TaskMasterTaskMissing(Exception):
        def __init__(self, message="TaskMaster task is missing"):
            super().__init__(message)
            logger.error(f"TaskMasterTaskMissing: {message}", extra={"char": "ROOT"})

    class TaskMasterTaskAlreadyCompleted(Exception):
        def __init__(self, message="TaskMaster task already completed"):
            super().__init__(message)
            logger.warning(f"TaskMasterTaskAlreadyCompleted: {message}", extra={"char": "ROOT"})

    class RecyclingItemNotRecyclable(Exception):
        def __init__(self, message="Item is not recyclable"):
            super().__init__(message)
            logger.error(f"RecyclingItemNotRecyclable: {message}", extra={"char": "ROOT"})

    class EquipmentTooMany(Exception):
        def __init__(self, message="Too many equipment items"):
            super().__init__(message)
            logger.warning(f"EquipmentTooMany: {message}", extra={"char": "ROOT"})

    class EquipmentAlreadyEquipped(Exception):
        def __init__(self, message="Equipment already equipped"):
            super().__init__(message)
            logger.warning(f"EquipmentAlreadyEquipped: {message}", extra={"char": "ROOT"})

    class EquipmentSlot(Exception):
        def __init__(self, message="Invalid equipment slot"):
            super().__init__(message)
            logger.error(f"EquipmentSlot: {message}", extra={"char": "ROOT"})

    class AlreadyAtDestination(Exception):
        def __init__(self, message="Already at destination"):
            super().__init__(message)
            logger.info(f"AlreadyAtDestination: {message}", extra={"char": "ROOT"})

    class BankFull(Exception):
        def __init__(self, message="Bank is full"):
            super().__init__(message)
            logger.warning(f"BankFull: {message}", extra={"char": "ROOT"})

    class TokenMissingorEmpty(Exception):
        def __init__(self, message="Token is missing or empty"):
            super().__init__(message)
            logger.critical(f"TokenMissingorEmpty: {message}", extra={"char": "ROOT"})
            exit(1)
                
    class NameAlreadyUsed(Exception):
        def __init__(self, message="Name already used"):
            super().__init__(message)
            logger.error(f"NameAlreadyUsed: {message}", extra={"char": "ROOT"})
    
    class MaxCharactersReached(Exception):
        def __init__(self, message="Max characters reached"):
            super().__init__(message)
            logger.warning(f"MaxCharactersReached: {message}", extra={"char": "ROOT"})


# --- Dataclasses ---
# --- Utility ---
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
class Content:
    type: str
    code: str

@dataclass
class TaskReward:
    items: Optional[List[dict]]
    gold: Optional[int]

@dataclass
class Effect:
    name: str
    value: int

@dataclass
class CraftingRecipe:
    skill: Optional[str]
    level: Optional[int]
    items: Optional[List[dict]]  # Example: [{'code': 'iron', 'quantity': 6}]
    quantity: Optional[int]

@dataclass
class AchievementReward:
    gold: int

# --- subclass related ---
@dataclass
class Item:
    name: str
    code: str
    level: int
    type: str
    subtype: Optional[str]
    description: Optional[str]
    effects: Optional[List[Effect]] = None
    craft: Optional[CraftingRecipe] = None
    tradeable: Optional[bool] = False

@dataclass
class Map:
    name: str
    code: str
    x: int
    y: int
    content: Content

@dataclass
class Monster:
    name: str
    code: str
    level: int
    hp: int
    attack_fire: int
    attack_earth: int
    attack_water: int
    attack_air: int
    res_fire: int
    res_earth: int
    res_water: int
    res_air: int
    min_gold: int
    max_gold: int
    drops: List[Drop]

@dataclass
class Resource:
    name: str
    code: str
    skill: Optional[str]
    level: int
    drops: List[Drop]

@dataclass
class Task:
    code: str
    level: int
    type: Optional[str]
    min_quantity: int
    max_quantity: int
    skill: Optional[str]
    rewards: Optional[TaskReward]

@dataclass
class Reward:
    code: str
    rate: int
    min_quantity: int
    max_quantity: int

@dataclass
class Achievement:
    name: str
    code: str
    description: str
    points: int
    type: str
    target: str
    total: int
    rewards: AchievementReward

# --- Other ---

@dataclass
class ContentMaps:
    api: "ArtifactsAPI"
    maps: Dict[str, ContentMap] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._cache_content_maps()
        self._initialize_attributes()

    def _cache_content_maps(self):
        """
        Fetch all content maps using `api.maps.get` and populate them based on content type.
        """
        try:
            logger.debug("Fetching all maps using api.maps.get()", extra={"char": self.api.char.name})
            all_maps = self.api.maps.get()  # Use the updated `get` method
            logger.debug(f"Retrieved {len(all_maps)} maps from the API", extra={"char": self.api.char.name})

            # Process each map and populate the maps dictionary
            for map_data in all_maps:
                x, y = map_data["x"], map_data["y"]
                content = map_data.get("content", {})
                if not content or not isinstance(content, dict):
                    continue

                content_type = content.get("type")
                content_code = content.get("code")

                # Fetch content-specific data
                if content_type == "monster":
                    monster = self.api.monsters.get(content_code)
                    name = monster.name
                    level = monster.level
                    skill = "combat"
                    drops = monster.drops
                elif content_type == "resource":
                    resource = self.api.resources.get(content_code)
                    name = resource.name
                    level = resource.level
                    skill = resource.skill
                    drops = resource.drops
                elif content_type == "workshop":
                    name = f"{content_code.capitalize()} Workshop"
                    level = None
                    skill = None
                    drops = []
                else:
                    name = f"{content_code.capitalize()}"
                    level = None
                    skill = None
                    drops = []

                position = Position(x, y)
                content_map = ContentMap(
                    name=name,
                    code=content_code,
                    level=level,
                    skill=skill,
                    pos=position,
                    drops=drops
                )

                # Handle duplicates based on Manhattan distance from (0, 0)
                if content_code in self.maps:
                    existing_map = self.maps[content_code]
                    new_distance = position.dist(Position(0, 0))
                    existing_distance = existing_map.pos.dist(Position(0, 0))
                    if new_distance < existing_distance:
                        self.maps[content_code] = content_map
                else:
                    self.maps[content_code] = content_map

            logger.debug(f"Finished caching {len(self.maps)} content maps", extra={"char": self.api.char.name})

        except Exception as e:
            logger.error(f"Error while caching content maps: {e}", extra={"char": "ROOT"})

    def _initialize_attributes(self):
        """
        Dynamically create attributes for each content map.
        """
        for map_code, content_map in self.maps.items():
            attribute_name = self._sanitize_attribute_name(map_code)
            setattr(self, attribute_name, content_map)

    @staticmethod
    def _sanitize_attribute_name(name: str) -> str:
        """
        Sanitize map codes to create valid Python attribute names.

        Args:
            name (str): The original map code.

        Returns:
            str: A sanitized attribute name.
        """
        return name.lower().replace(" ", "_").replace("-", "_")

    def get_map(self, code: str) -> Optional[ContentMap]:
        """
        Retrieve a specific content map by its code.

        Args:
            code (str): The unique code for the content map.

        Returns:
            ContentMap or None: The content map if found, otherwise None.
        """
        return self.maps.get(code)

    def get_all_maps(self) -> List[ContentMap]:
        """
        Retrieve all cached content maps.

        Returns:
            List[ContentMap]: List of all cached content maps.
        """
        return list(self.maps.values())

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
        
        if _re_cache(self.api, "item_cache"):
            db_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_cache  (
                name TEXT PRIMARY KEY,
                code TEXT,
                type TEXT,
                subtype TEXT,
                description TEXT,
                effects TEXT,
                craft TEXT,
                tradeable BOOL
            )
            """
            )
            db.commit()
                    
            endpoint = "items?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_items")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of items", extra={"char": self.api.char.name})

            all_items = []
            for i in range(pages):
                endpoint = f"items?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_items", include_headers=True)
                item_list = res["json"]["data"]


                for item in item_list:
                    name = item["name"]
                    code = item["code"]
                    type_ = item["type"]
                    subtype = item.get("subtype", "")
                    description = item.get("description", "")
                    effects = json.dumps(item.get("effects", []))  # Serialize the effects as JSON
                    craft = json.dumps(item["craft"]) if item.get("craft") else None  # Serialize craft if available
                    tradeable = item.get("tradeable", False)

                    # Insert the item into the database
                    db.execute("""
                    INSERT OR REPLACE INTO item_cache (name, code, type, subtype, description, effects, craft, tradeable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (name, code, type_, subtype, description, effects, craft, tradeable))
                    
                    db.commit()


            self.cache = {item.code: item for item in all_items}
            self.all_items = all_items

            logger.debug(f"Finished caching {len(all_items)} items", extra={"char": self.api.char.name})

    def _filter_items(self, craft_material=None, craft_skill=None, max_level=None, min_level=None, 
                      name=None, item_type=None):

        # Base SQL query to select all items
        query = "SELECT * FROM item_cache WHERE 1=1"
        params = []

        # Apply filters to the query
        if craft_material:
            query += " AND EXISTS (SELECT 1 FROM json_each(json_extract(item_cache.craft, '$.items')) WHERE json_each.value LIKE ?)"
            params.append(f"%{craft_material}%")
        
        if craft_skill:
            query += " AND json_extract(item_cache.craft, '$.skill') = ?"
            params.append(craft_skill)

        if max_level is not None:
            query += " AND item_cache.level <= ?"
            params.append(max_level)

        if min_level is not None:
            query += " AND item_cache.level >= ?"
            params.append(min_level)

        if name:
            name_pattern = f"%{name}%"
            query += " AND item_cache.name LIKE ?"
            params.append(name_pattern)

        if item_type:
            query += " AND item_cache.type = ?"
            params.append(item_type)

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Close the connection
        db_cursor.close()
        db.close()

        # Return the filtered items
        return rows

    def get(self, item_code=None, **filters):
        """
        Get a specific item by its code or filter items based on the provided parameters.

        Args:
            item_code (str, optional): The code of a specific item to retrieve.
            filters (dict, optional): A dictionary of filter parameters. Supported filters:
                - craft_material (str): Filter by the code of the craft material used by the item.
                - craft_skill (str): Filter by the craft skill required for the item.
                - max_level (int): Filter items with a level less than or equal to the specified value.
                - min_level (int): Filter items with a level greater than or equal to the specified value.
                - name (str): Search for items whose names match the given pattern (case-insensitive).
                - item_type (str): Filter by item type (e.g., 'weapon', 'armor', etc.).

        Returns:
            dict or list: Returns a single item if `item_code` is provided, or a list of items
            matching the filter criteria if `filters` are provided.
        """

        if not self.all_items:
            self._cache_items()
        if item_code:
            return self.cache.get(item_code)
        return self._filter_items(**filters)

class Maps:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_maps = []

    def _cache_maps(self):
        if _re_cache(self.api, "map_cache"):
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS map_cache (
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                content_code TEXT,
                content_type TEXT,
                PRIMARY KEY (x, y)
            )
            """)
            db.commit()

            endpoint = "maps?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_maps")
            pages = math.ceil(int(res["pages"]) / 100)
            
            logger.debug(f"Caching {pages} pages of maps", extra={"char": self.api.char.name})
            
            all_maps = []
            for i in range(pages):
                endpoint = f"maps?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_maps")
                map_list = res["data"]
                
                for map_item in map_list:
                    x = map_item['x']
                    y = map_item['y']
                    content_code = map_item.get('content_code', '')
                    content_type = map_item.get('content_type', '')
                    
                    # Insert or replace the map into the database
                    db.execute("""
                    INSERT OR REPLACE INTO map_cache (x, y, content_code, content_type)
                    VALUES (?, ?, ?, ?)
                    """, (x, y, content_code, content_type))
                    db.commit()
                    
                    all_maps.append(map_item)

                logger.debug(f"Fetched {len(map_list)} maps from page {i+1}", extra={"char": self.api.char.name})

            self.cache = {f"{item['x']}/{item['y']}": item for item in all_maps}
            self.all_maps = all_maps

            logger.debug(f"Finished caching {len(all_maps)} maps", extra={"char": self.api.char.name})

    def _filter_maps(self, map_content=None, content_type=None):
        # Base SQL query to select all maps
        query = "SELECT * FROM map_cache WHERE 1=1"
        params = []

        # Apply filters to the query
        if map_content:
            query += " AND content_code LIKE ?"
            params.append(f"%{map_content}%")

        if content_type:
            query += " AND content_type = ?"
            params.append(content_type)

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Return the filtered maps
        return rows

    def get(self, x=None, y=None, **filters):
        """
        Retrieves a specific map by coordinates or filters maps based on provided parameters.
        
        Args:
            x (int, optional): Map's X coordinate.
            y (int, optional): Map's Y coordinate.
            **filters: Optional filter parameters. Supported filters:
                - map_content: Search maps by content (case-insensitive).
                - content_type: Filter maps by content type.

        Returns:
            dict or list: A specific map if coordinates are provided, else a filtered list of maps.
        """
        if not self.all_maps:
            self._cache_maps()
        if x is not None and y is not None:
            return self.cache.get(f"{x}/{y}")
        return self._filter_maps(**filters)

class Monsters:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_monsters = []

    def _cache_monsters(self):
        if _re_cache(self.api, "monster_cache"):
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS monster_cache (
                code TEXT PRIMARY KEY,
                name TEXT,
                level INTEGER,
                hp INTEGER,
                attack_fire INTEGER,
                attack_earth INTEGER,
                attack_water INTEGER,
                attack_air INTEGER,
                res_fire INTEGER,
                res_earth INTEGER,
                res_water INTEGER,
                res_air INTEGER,
                min_gold INTEGER,
                max_gold INTEGER,
                drops TEXT
            )
            """)
            db.commit()

            endpoint = "monsters?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_monsters")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of monsters", extra={"char": self.api.char.name})

            all_monsters = []
            for i in range(pages):
                endpoint = f"monsters?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_monsters")
                monster_list = res["data"]

                for monster in monster_list:
                    code = monster["code"]
                    name = monster["name"]
                    level = monster["level"]
                    hp = monster["hp"]
                    attack_fire = monster["attack_fire"]
                    attack_earth = monster["attack_earth"]
                    attack_water = monster["attack_water"]
                    attack_air = monster["attack_air"]
                    res_fire = monster["res_fire"]
                    res_earth = monster["res_earth"]
                    res_water = monster["res_water"]
                    res_air = monster["res_air"]
                    min_gold = monster["min_gold"]
                    max_gold = monster["max_gold"]
                    drops = json.dumps([Drop(**drop).__dict__ for drop in monster["drops"]])  # Serialize drops as JSON

                    # Insert or replace the monster into the database
                    db.execute("""
                    INSERT OR REPLACE INTO monster_cache (
                        code, name, level, hp, attack_fire, attack_earth, attack_water, attack_air,
                        res_fire, res_earth, res_water, res_air, min_gold, max_gold, drops
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (code, name, level, hp, attack_fire, attack_earth, attack_water, attack_air,
                        res_fire, res_earth, res_water, res_air, min_gold, max_gold, drops))
                    db.commit()

                    all_monsters.append(monster)

                logger.debug(f"Fetched {len(monster_list)} monsters from page {i+1}", extra={"char": self.api.char.name})

            self.cache = {monster["code"]: monster for monster in all_monsters}
            self.all_monsters = all_monsters

            logger.debug(f"Finished caching {len(all_monsters)} monsters", extra={"char": self.api.char.name})
            
    def _filter_monsters(self, drop=None, max_level=None, min_level=None):
        # Base SQL query to select all monsters
        query = "SELECT * FROM monster_cache WHERE 1=1"
        params = []

        # Apply filters to the query
        if drop:
            query += " AND EXISTS (SELECT 1 FROM json_each(json_extract(monster_cache.drops, '$')) WHERE json_each.value LIKE ?)"
            params.append(f"%{drop}%")

        if max_level is not None:
            query += " AND monster_cache.level <= ?"
            params.append(max_level)

        if min_level is not None:
            query += " AND monster_cache.level >= ?"
            params.append(min_level)

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Return the filtered monsters
        return rows

    def get(self, monster_code=None, **filters):
        """
        Retrieves a specific monster or filters monsters based on provided parameters.
        
        Args:
            monster_code (str, optional): Retrieve monster by its unique code.
            **filters: Optional filter parameters. Supported filters:
                - drop: Filter monsters that drop a specific item.
                - max_level: Filter by maximum monster level.
                - min_level: Filter by minimum monster level.

        Returns:
            dict or list: A single monster if monster_code is provided, else a filtered list of monsters.
        """
        if not self.all_monsters:
            self._cache_monsters()
        if monster_code:
            return self.cache.get(monster_code)
        return self._filter_monsters(**filters)

class Resources:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_resources = []

    def _cache_resources(self):
        if _re_cache(self.api, "resource_cache"):
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_cache (
                code TEXT PRIMARY KEY,
                name TEXT,
                skill TEXT,
                level INTEGER,
                drops TEXT
            )
            """)
            db.commit()

            endpoint = "resources?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_resources")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of resources", extra={"char": self.api.char.name})

            all_resources = []
            for i in range(pages):
                endpoint = f"resources?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_resources")
                resource_list = res["data"]

                for resource in resource_list:
                    code = resource["code"]
                    name = resource["name"]
                    skill = resource.get("skill")
                    level = resource["level"]
                    drops = json.dumps([Drop(**drop).__dict__ for drop in resource.get("drops", [])])  # Serialize drops as JSON

                    # Insert or replace the resource into the database
                    db.execute("""
                    INSERT OR REPLACE INTO resource_cache (
                        code, name, skill, level, drops
                    ) VALUES (?, ?, ?, ?, ?)
                    """, (code, name, skill, level, drops))
                    db.commit()

                    all_resources.append(resource)

                logger.debug(f"Fetched {len(resource_list)} resources from page {i+1}", extra={"char": self.api.char.name})

            self.cache = {resource["code"]: resource for resource in all_resources}
            self.all_resources = all_resources

            logger.debug(f"Finished caching {len(all_resources)} resources", extra={"char": self.api.char.name})

    def _filter_resources(self, drop=None, max_level=None, min_level=None, skill=None):
        # Base SQL query to select all resources
        query = "SELECT * FROM resource_cache WHERE 1=1"
        params = []

        # Apply filters to the query
        if drop:
            query += " AND EXISTS (SELECT 1 FROM json_each(json_extract(resource_cache.drops, '$')) WHERE json_each.value LIKE ?)"
            params.append(f"%{drop}%")

        if max_level is not None:
            query += " AND resource_cache.level <= ?"
            params.append(max_level)

        if min_level is not None:
            query += " AND resource_cache.level >= ?"
            params.append(min_level)

        if skill:
            query += " AND resource_cache.skill = ?"
            params.append(skill)

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Return the filtered resources
        return rows

    def get(self, resource_code=None, **filters):
        """
        Retrieves a specific resource or filters resources based on provided parameters.
        
        Args:
            resource_code (str, optional): Retrieve resource by its unique code.
            **filters: Optional filter parameters. Supported filters:
                - drop: Filter resources that drop a specific item.
                - max_level: Filter by maximum resource level.
                - min_level: Filter by minimum resource level.
                - skill: Filter by craft skill.

        Returns:
            dict or list: A single resource if resource_code is provided, else a filtered list of resources.
        """
        if not self.all_resources:
            self._cache_resources()
        if resource_code:
            return self.cache.get(resource_code)
        return self._filter_resources(**filters)

class Tasks:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_tasks = []

    def _cache_tasks(self):
        if _re_cache(self.api, "task_cache"):
            # Create table if it doesn't exist
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_cache (
                code TEXT PRIMARY KEY,
                level INTEGER,
                type TEXT,
                min_quantity INTEGER,
                max_quantity INTEGER,
                skill TEXT,
                rewards TEXT
            )
            """)
            db.commit()

            endpoint = "tasks/list?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_tasks")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of tasks", extra={"char": self.api.char.name})

            all_tasks = []
            for i in range(pages):
                endpoint = f"tasks/list?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_tasks")
                task_list = res["data"]

                for task in task_list:
                    code = task["code"]
                    level = task["level"]
                    task_type = task.get("type")
                    min_quantity = task["min_quantity"]
                    max_quantity = task["max_quantity"]
                    skill = task.get("skill")
                    rewards = json.dumps({
                        "items": [{"code": item["code"], "quantity": item["quantity"]} for item in task["rewards"].get("items", [])],
                        "gold": task["rewards"].get("gold", 0)
                    }) if task.get("rewards") else None

                    # Insert or replace the task into the database
                    db.execute("""
                    INSERT OR REPLACE INTO task_cache (
                        code, level, type, min_quantity, max_quantity, skill, rewards
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (code, level, task_type, min_quantity, max_quantity, skill, rewards))
                    db.commit()

                    all_tasks.append(task)

                logger.debug(f"Fetched {len(task_list)} tasks from page {i+1}", extra={"char": self.api.char.name})

            self.cache = {task["code"]: task for task in all_tasks}
            self.all_tasks = all_tasks

            logger.debug(f"Finished caching {len(all_tasks)} tasks", extra={"char": self.api.char.name})

    def _filter_tasks(self, skill=None, task_type=None, max_level=None, min_level=None, name=None):
        # Base SQL query to select all tasks
        query = "SELECT * FROM task_cache WHERE 1=1"
        params = []

        # Apply filters to the query
        if skill:
            query += " AND task_cache.skill = ?"
            params.append(skill)

        if task_type:
            query += " AND task_cache.type = ?"
            params.append(task_type)

        if max_level is not None:
            query += " AND task_cache.level <= ?"
            params.append(max_level)

        if min_level is not None:
            query += " AND task_cache.level >= ?"
            params.append(min_level)

        if name:
            query += " AND task_cache.code LIKE ?"
            params.append(f"%{name}%")

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Reconstruct tasks from the database rows
        filtered_tasks = []
        for row in rows:
            task = Task(
                code=row[0],
                level=row[1],
                type=row[2],
                min_quantity=row[3],
                max_quantity=row[4],
                skill=row[5],
                rewards=json.loads(row[6]) if row[6] else None
            )
            filtered_tasks.append(task)

        return filtered_tasks

    def get(self, task_code=None, **filters):
        """
        Retrieves a specific task or filters tasks based on provided parameters.
        
        Args:
            task_code (str, optional): Retrieve task by its unique code.
            **filters: Optional filter parameters. Supported filters:
                - skill: Filter by task skill.
                - task_type: Filter by task type.
                - max_level: Filter by maximum task level.
                - min_level: Filter by minimum task level.
                - name: Filter by task name (case-insensitive).

        Returns:
            dict or list: A single task if task_code is provided, else a filtered list of tasks.
        """
        if not self.all_tasks:
            self._cache_tasks()
        if task_code:
            return self.cache.get(task_code)
        return self._filter_tasks(**filters)

class Rewards:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_rewards = []

    def _cache_rewards(self):
        if _re_cache(self.api, "reward_cache"):
            # Create table if it doesn't exist
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS reward_cache (
                code TEXT PRIMARY KEY,
                rate INTEGER,
                min_quantity INTEGER,
                max_quantity INTEGER
            )
            """)
            db.commit()

            endpoint = "tasks/rewards?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_task_rewards")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of task rewards", extra={"char": self.api.char.name})

            all_rewards = []
            for i in range(pages):
                endpoint = f"tasks/rewards?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_task_rewards")
                reward_list = res["data"]

                for reward in reward_list:
                    code = reward["code"]
                    rate = reward["rate"]
                    min_quantity = reward["min_quantity"]
                    max_quantity = reward["max_quantity"]

                    # Insert or replace the reward into the database
                    db.execute("""
                    INSERT OR REPLACE INTO reward_cache (
                        code, rate, min_quantity, max_quantity
                    ) VALUES (?, ?, ?, ?)
                    """, (code, rate, min_quantity, max_quantity))
                    db.commit()

                    all_rewards.append(reward)

                logger.debug(f"Fetched {len(reward_list)} task rewards from page {i+1}", extra={"char": self.api.char.name})

            self.rewards_cache = {reward["code"]: reward for reward in all_rewards}
            self.all_rewards = all_rewards

            logger.debug(f"Finished caching {len(all_rewards)} task rewards", extra={"char": self.api.char.name})

    def _filter_rewards(self, name=None):
        # Base SQL query to select all rewards
        query = "SELECT * FROM reward_cache WHERE 1=1"
        params = []

        if name:
            query += " AND reward_cache.code LIKE ?"
            params.append(f"%{name}%")

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Reconstruct rewards from the database rows
        filtered_rewards = []
        for row in rows:
            reward = Reward(
                code=row[0],
                rate=row[1],
                min_quantity=row[2],
                max_quantity=row[3]
            )
            filtered_rewards.append(reward)

        return filtered_rewards

    def get_all_rewards(self, **filters):
        logger.debug(f"Getting all task rewards with filters: {filters}", extra={"char": self.api.char.name})
        
        if not self.all_rewards:
            logger.debug("Rewards cache is empty, calling _cache_rewards() to load rewards.", 
                        extra={"char": self.api.char.name})
            self._cache_rewards()

        return self._filter_rewards(**filters)

    def get(self, task_code=None):
        """
        Retrieves a specific reward or filters rewards based on provided parameters.
        
        Args:
            reward_code (str, optional): Retrieve reward by its unique code.

        Returns:
            dict or list: A single reward if reward_code is provided, else a filtered list of rewards.
        """
        if not self.all_rewards:
            logger.debug("Rewards cache is empty, calling _cache_rewards() to load rewards.", 
                        extra={"char": self.api.char.name})
            self._cache_rewards()

        if task_code:
            reward = self.rewards_cache.get(task_code)
            if reward:
                logger.debug(f"Found reward with code {task_code}", extra={"char": self.api.char.name})
            else:
                logger.debug(f"Reward with code {task_code} not found in cache", extra={"char": self.api.char.name})
            return reward

class Achievements:
    def __init__(self, api: "ArtifactsAPI"):
        self.api = api
        self.cache = {}
        self.all_achievements = []

    def _cache_achievements(self):
        if _re_cache(self.api, "achievement_cache"):
            # Create table if it doesn't exist
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievement_cache (
                code TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                points INTEGER,
                type TEXT,
                target INTEGER,
                total INTEGER,
                rewards_gold INTEGER
            )
            """)
            db.commit()

            endpoint = "achievements?size=1"
            res = self.api._make_request("GET", endpoint, source="get_all_achievements")
            pages = math.ceil(int(res["pages"]) / 100)

            logger.debug(f"Caching {pages} pages of achievements", extra={"char": self.api.char.name})

            all_achievements = []
            for i in range(pages):
                endpoint = f"achievements?size=100&page={i+1}"
                res = self.api._make_request("GET", endpoint, source="get_all_achievements")
                achievement_list = res["data"]

                for achievement in achievement_list:
                    code = achievement["code"]
                    name = achievement["name"]
                    description = achievement["description"]
                    points = achievement["points"]
                    type = achievement["type"]
                    target = achievement["target"]
                    total = achievement["total"]
                    rewards_gold = achievement["rewards"].get("gold", 0)

                    # Insert or replace the achievement into the database
                    db.execute("""
                    INSERT OR REPLACE INTO achievement_cache (
                        code, name, description, points, type, target, total, rewards_gold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (code, name, description, points, type, target, total, rewards_gold))
                    db.commit()

                    all_achievements.append(achievement)

                logger.debug(f"Fetched {len(achievement_list)} achievements from page {i+1}", extra={"char": self.api.char.name})

            self.cache = {achievement["code"]: achievement for achievement in all_achievements}
            self.all_achievements = all_achievements

            logger.debug(f"Finished caching {len(all_achievements)} achievements", extra={"char": self.api.char.name})

    def _filter_achievements(self, achievement_type=None, name=None, description=None, reward_type=None,
                            reward_item=None, points_min=None, points_max=None):
        # Base SQL query to select all achievements
        query = "SELECT * FROM achievement_cache WHERE 1=1"
        params = []

        if achievement_type:
            query += " AND achievement_cache.type = ?"
            params.append(achievement_type)
        if name:
            query += " AND achievement_cache.name LIKE ?"
            params.append(f"%{name}%")
        if description:
            query += " AND achievement_cache.description LIKE ?"
            params.append(f"%{description}%")
        if reward_type:
            query += " AND EXISTS (SELECT 1 FROM reward_cache WHERE reward_cache.type = ? AND reward_cache.code IN (SELECT reward_code FROM achievement_rewards WHERE achievement_code = achievement_cache.code))"
            params.append(reward_type)
        if reward_item:
            query += " AND EXISTS (SELECT 1 FROM reward_cache WHERE reward_cache.code = ? AND reward_cache.code IN (SELECT reward_code FROM achievement_rewards WHERE achievement_code = achievement_cache.code))"
            params.append(reward_item)
        if points_min is not None:
            query += " AND achievement_cache.points >= ?"
            params.append(points_min)
        if points_max is not None:
            query += " AND achievement_cache.points <= ?"
            params.append(points_max)

        # Execute the query
        db_cursor.execute(query, params)
        rows = db_cursor.fetchall()

        # Reconstruct achievements from the database rows
        filtered_achievements = []
        for row in rows:
            achievement = Achievement(
                name=row[1],
                code=row[0],
                description=row[2],
                points=row[3],
                type=row[4],
                target=row[5],
                total=row[6],
                rewards=AchievementReward(gold=row[7])
            )
            filtered_achievements.append(achievement)

        return filtered_achievements

    def get(self, achievement_code=None, **filters):
        """
        Retrieves a specific achievement or filters achievements based on provided parameters.
        
        Args:
            achievement_code (str, optional): Retrieve achievement by its unique code.
            **filters: Optional filter parameters. Supported filters:
                - achievement_type: Filter by achievement type.
                - name: Filter by achievement name (case-insensitive).
                - description: Filter by achievement description (case-insensitive).
                - reward_type: Filter by reward type.
                - reward_item: Filter by reward item code.
                - points_min: Filter by minimum achievement points.
                - points_max: Filter by maximum achievement points.

        Returns:
            dict or list: A single achievement if achievement_code is provided, else a filtered list of achievements.
        """
        if not self.all_achievements:
            self._cache_achievements()
        if achievement_code:
            return self.cache.get(achievement_code)
        return self._filter_achievements(**filters)

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
    def get_history(self, item_code: str, buyer: Optional[str] = None, seller: Optional[str] = None, page: int = 1, size: int = 100) -> dict:
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
        query = f"size={size}&page={page}"
        if buyer:
            query += f"&buyer={buyer}"
        if seller:
            query += f"&seller={seller}"
        endpoint = f"grandexchange/history/{item_code}?{query}"
        return self.api._make_request("GET", endpoint, source="get_ge_history").get("data")

    def get_sell_orders(self, item_code: Optional[str] = None, seller: Optional[str] = None, page: int = 1, size: int = 100) -> dict:
        """
        Retrieve a list of sell orders on the Grand Exchange with optional filters.

        Args:
            item_code (Optional[str]): Filter by item code.
            seller (Optional[str]): Filter by seller name.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of sell orders.
        """
        query = f"size={size}&page={page}"
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
    
    # --- Grand Exchange Actions Functions ---
    def buy(self, order_id: str, quantity: int = 1) -> dict:
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

    def sell(self, item_code: str, price: int, quantity: int = 1) -> dict:
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

    def cancel(self, order_id: str) -> dict:
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
        self.task_rewards = Rewards(self)
        self.achievments = Achievements(self)
        self.leaderboard = Leaderboard(self)
        self.accounts = Accounts(self)
        self.content_maps = ContentMaps(self)

        self.logger.debug("Finished instantiating wrapper for " + character_name, extra = {"char": character_name})

    @with_cooldown
    def _make_request(self, method: str, endpoint: str, json: Optional[dict] = None, 
                    source: Optional[str] = None, retries: int = 3, include_headers: bool = False) -> dict:
        """
        Makes an API request and returns the JSON response.
        Optionally returns response headers when include_headers is True.
        Now managed by cooldown decorator.
        """
        try:
            endpoint = endpoint.strip("/")
            url = f"{self.base_url}/{endpoint}"
            if source != "get_character":
                self.logger.debug(f"Sending API request to {url} with the following json:\n{json}", extra={"char": self.character_name})

            response = requests.request(method, url, headers=self.headers, json=json, timeout=10)

            if response.status_code != 200:
                message = f"An error occurred. Returned code {response.status_code}, {response.json().get('error', {}).get('message', '')} Endpoint: {endpoint}"
                message += f", Body: {json}" if json else ""
                message += f", Source: {source}" if source else ""

                self._raise(response.status_code, message)

            if source != "get_character":
                self.get_character()
            
            # Return headers if the flag is set
            if include_headers:
                return {
                    "json": response.json(),
                    "headers": dict(response.headers)
                }

            return response.json()

        except Exception as e:
            if "Character already at destination" not in str(e):
                if retries:
                    retries -= 1
                    logger.warning(f"Retrying, {retries} retries left", extra={"char": self.character_name})
                    return self._make_request(method, endpoint, json, source, retries, include_headers)

    def _get_version(self):
        version = self._make_request(endpoint="", method="GET").get("data").get("version")
        return version
    
    def _cache(self):
        self.maps._cache_maps()
        self.items._cache_items()
        self.monsters._cache_monsters()
        self.resources._cache_resources()
        self.tasks._cache_tasks()
        self.task_rewards._cache_rewards()
        self.achievments._cache_achievements()
        
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
            case _:
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

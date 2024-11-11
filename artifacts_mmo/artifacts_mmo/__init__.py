import requests
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime

debug=False

# --- Exceptions ---
class APIException(Exception):
    """Base exception class for API errors"""
    class CharacterInCooldown(Exception):
        pass

    class NotFound(Exception):
        pass

    class ActionAlreadyInProgress(Exception):
        pass

    class CharacterNotFound(Exception):
        pass

    class TooLowLevel(Exception):
        pass

    class InventoryFull(Exception):
        pass

    class MapItemNotFound(Exception):
        pass

    class InsufficientQuantity(Exception):
        pass

    class GETooMany(Exception):
        pass

    class GENoStock(Exception):
        pass

    class GENoItem(Exception):
        pass

    class TransactionInProgress(Exception):
        pass

    class InsufficientGold(Exception):
        pass

    class TaskMasterNoTask(Exception):
        pass

    class TaskMasterAlreadyHasTask(Exception):
        pass

    class TaskMasterTaskNotComplete(Exception):
        pass

    class TaskMasterTaskMissing(Exception):
        pass

    class TaskMasterTaskAlreadyCompleted(Exception):
        pass

    class RecyclingItemNotRecyclable(Exception):
        pass

    class EquipmentTooMany(Exception):
        pass

    class EquipmentAlreadyEquipped(Exception):
        pass

    class EquipmentSlot(Exception):
        pass

    class AlreadyAtDestination(Exception):
        pass

    class BankFull(Exception):
        pass

    class TokenMissingorEmpty(Exception):
        pass
    
    class NameAlreadyUsed(Exception):
        pass
    
    class MaxCharactersReached(Exception):
        pass
# --- End Exceptions ---


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
        
        Parameters:
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
    salmon_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Salmon Fishing Spot", code="salmon_fishing_spot", level=40, skill="fishing", pos=Position(-2, -4), drops=['Drop(code="salmon", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)']))
    bandit_lizard: ContentMap = field(default_factory=lambda: ContentMap(name="Bandit Lizard", code="bandit_lizard", level=25, skill="combat", pos=Position(-1, -4), drops=['Drop(code="bandit_armor", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="lizard_skin", rate=12, min_quantity=1, max_quantity=1)']))
    goblin_wolfrider: ContentMap = field(default_factory=lambda: ContentMap(name="Goblin Wolfrider", code="goblin_wolfrider", level=40, skill="combat", pos=Position(6, -4), drops=['Drop(code="broken_sword", rate=24, min_quantity=1, max_quantity=1)', 'Drop(code="wolfrider_hair", rate=12, min_quantity=1, max_quantity=1)']))
    orc: ContentMap = field(default_factory=lambda: ContentMap(name="Orc", code="orc", level=38, skill="combat", pos=Position(7, -2), drops=['Drop(code="orc_skin", rate=12, min_quantity=1, max_quantity=1)']))
    ogre: ContentMap = field(default_factory=lambda: ContentMap(name="Ogre", code="ogre", level=20, skill="combat", pos=Position(8, -2), drops=['Drop(code="ogre_eye", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="ogre_skin", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="wooden_club", rate=100, min_quantity=1, max_quantity=1)']))
    pig: ContentMap = field(default_factory=lambda: ContentMap(name="Pig", code="pig", level=19, skill="combat", pos=Position(-3, -3), drops=['Drop(code="pig_skin", rate=12, min_quantity=1, max_quantity=1)']))
    woodcutting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Pig", code="woodcutting", level=19, skill="combat", pos=Position(-2, -3), drops=['Drop(code="pig_skin", rate=12, min_quantity=1, max_quantity=1)']))
    gold_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Gold Rocks", code="gold_rocks", level=30, skill="mining", pos=Position(6, -3), drops=['Drop(code="gold_ore", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)']))
    cyclops: ContentMap = field(default_factory=lambda: ContentMap(name="Cyclops", code="cyclops", level=25, skill="combat", pos=Position(7, -3), drops=['Drop(code="cyclops_eye", rate=12, min_quantity=1, max_quantity=1)']))
    blue_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Blue Slime", code="blue_slime", level=6, skill="combat", pos=Position(0, -2), drops=['Drop(code="blue_slimeball", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)']))
    yellow_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Yellow Slime", code="yellow_slime", level=2, skill="combat", pos=Position(1, -2), drops=['Drop(code="yellow_slimeball", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)']))
    red_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Red Slime", code="red_slime", level=7, skill="combat", pos=Position(1, -1), drops=['Drop(code="red_slimeball", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)']))
    green_slime: ContentMap = field(default_factory=lambda: ContentMap(name="Green Slime", code="green_slime", level=4, skill="combat", pos=Position(0, -1), drops=['Drop(code="green_slimeball", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="apple", rate=20, min_quantity=1, max_quantity=1)']))
    goblin: ContentMap = field(default_factory=lambda: ContentMap(name="Goblin", code="goblin", level=35, skill="combat", pos=Position(6, -2), drops=['Drop(code="goblin_tooth", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="goblin_eye", rate=12, min_quantity=1, max_quantity=1)']))
    wolf: ContentMap = field(default_factory=lambda: ContentMap(name="Wolf", code="wolf", level=15, skill="combat", pos=Position(-2, 1), drops=['Drop(code="raw_wolf_meat", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="wolf_bone", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="wolf_hair", rate=12, min_quantity=1, max_quantity=1)']))
    ash_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Ash Tree", code="ash_tree", level=1, skill="woodcutting", pos=Position(-1, 0), drops=['Drop(code="ash_wood", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)']))
    copper_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Copper Rocks", code="copper_rocks", level=1, skill="mining", pos=Position(2, 0), drops=['Drop(code="copper_ore", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)']))
    chicken: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="chicken", level=1, skill="combat", pos=Position(0, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    cooking_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="cooking", level=1, skill="combat", pos=Position(1, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    weaponcrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="weaponcrafting", level=1, skill="combat", pos=Position(2, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    gearcrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="gearcrafting", level=1, skill="combat", pos=Position(3, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    bank: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="bank", level=1, skill="combat", pos=Position(4, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    grand_exchange: ContentMap = field(default_factory=lambda: ContentMap(name="Chicken", code="grand_exchange", level=1, skill="combat", pos=Position(5, 1), drops=['Drop(code="raw_chicken", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="egg", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="feather", rate=8, min_quantity=1, max_quantity=1)']))
    owlbear: ContentMap = field(default_factory=lambda: ContentMap(name="Owlbear", code="owlbear", level=30, skill="combat", pos=Position(10, 1), drops=['Drop(code="owlbear_hair", rate=12, min_quantity=1, max_quantity=1)']))      
    cow: ContentMap = field(default_factory=lambda: ContentMap(name="Cow", code="cow", level=8, skill="combat", pos=Position(0, 2), drops=['Drop(code="raw_beef", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="milk_bucket", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="cowhide", rate=8, min_quantity=1, max_quantity=1)']))
    taskmaster_monsters: ContentMap = field(default_factory=lambda: ContentMap(name="Cow", code="monsters", level=8, skill="combat", pos=Position(1, 2), drops=['Drop(code="raw_beef", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="milk_bucket", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="cowhide", rate=8, min_quantity=1, max_quantity=1)']))
    sunflower: ContentMap = field(default_factory=lambda: ContentMap(name="Sunflower", code="sunflower", level=1, skill="alchemy", pos=Position(2, 2), drops=['Drop(code="sunflower", rate=1, min_quantity=1, max_quantity=1)']))     
    gudgeon_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Gudgeon Fishing Spot", code="gudgeon_fishing_spot", level=1, skill="fishing", pos=Position(4, 2), drops=['Drop(code="gudgeon", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)']))
    shrimp_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Shrimp Fishing Spot", code="shrimp_fishing_spot", level=10, skill="fishing", pos=Position(5, 2), drops=['Drop(code="shrimp", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)']))
    jewelrycrafting_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Owlbear", code="jewelrycrafting", level=30, skill="combat", pos=Position(1, 3), drops=['Drop(code="owlbear_hair", rate=12, min_quantity=1, max_quantity=1)']))
    alchemy_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Owlbear", code="alchemy", level=30, skill="combat", pos=Position(2, 3), drops=['Drop(code="owlbear_hair", rate=12, min_quantity=1, max_quantity=1)']))       
    mushmush: ContentMap = field(default_factory=lambda: ContentMap(name="Mushmush", code="mushmush", level=10, skill="combat", pos=Position(5, 3), drops=['Drop(code="mushroom", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="forest_ring", rate=100, min_quantity=1, max_quantity=1)']))
    flying_serpent: ContentMap = field(default_factory=lambda: ContentMap(name="Flying Serpent", code="flying_serpent", level=12, skill="combat", pos=Position(5, 4), drops=['Drop(code="flying_wing", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="serpent_skin", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="forest_ring", rate=100, min_quantity=1, max_quantity=1)']))
    mining_workshop: ContentMap = field(default_factory=lambda: ContentMap(name="Flying Serpent", code="mining", level=12, skill="combat", pos=Position(1, 5), drops=['Drop(code="flying_wing", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="serpent_skin", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="forest_ring", rate=100, min_quantity=1, max_quantity=1)']))
    birch_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Birch Tree", code="birch_tree", level=20, skill="woodcutting", pos=Position(3, 5), drops=['Drop(code="birch_wood", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)']))
    coal_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Coal Rocks", code="coal_rocks", level=20, skill="mining", pos=Position(1, 6), drops=['Drop(code="coal", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="topaz_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="topaz", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="ruby", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="ruby_stone", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire", rate=5000, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire_stone", rate=600, min_quantity=1, max_quantity=1)']))
    spruce_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Spruce Tree", code="spruce_tree", level=10, skill="woodcutting", pos=Position(2, 6), drops=['Drop(code="spruce_wood", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="apple", rate=10, min_quantity=1, max_quantity=1)']))
    skeleton: ContentMap = field(default_factory=lambda: ContentMap(name="Skeleton", code="skeleton", level=18, skill="combat", pos=Position(8, 6), drops=['Drop(code="skeleton_bone", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="skeleton_skull", rate=16, min_quantity=1, max_quantity=1)']))
    dead_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Dead Tree", code="dead_tree", level=30, skill="woodcutting", pos=Position(9, 6), drops=['Drop(code="dead_wood", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="sap", rate=10, min_quantity=1, max_quantity=1)']))
    vampire: ContentMap = field(default_factory=lambda: ContentMap(name="Vampire", code="vampire", level=24, skill="combat", pos=Position(10, 6), drops=['Drop(code="vampire_blood", rate=12, min_quantity=1, max_quantity=1)']))     
    iron_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Iron Rocks", code="iron_rocks", level=10, skill="mining", pos=Position(1, 7), drops=['Drop(code="iron_ore", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="topaz_stone", rate=500, min_quantity=1, max_quantity=1)', 'Drop(code="topaz", rate=4000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald", rate=4000, min_quantity=1, max_quantity=1)', 'Drop(code="emerald_stone", rate=500, min_quantity=1, max_quantity=1)', 'Drop(code="ruby", rate=4000, min_quantity=1, max_quantity=1)', 'Drop(code="ruby_stone", rate=500, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire", rate=4000, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire_stone", rate=500, min_quantity=1, max_quantity=1)']))
    death_knight: ContentMap = field(default_factory=lambda: ContentMap(name="Death Knight", code="death_knight", level=28, skill="combat", pos=Position(8, 7), drops=['Drop(code="death_knight_sword", rate=600, min_quantity=1, max_quantity=1)', 'Drop(code="red_cloth", rate=12, min_quantity=1, max_quantity=1)']))
    lich: ContentMap = field(default_factory=lambda: ContentMap(name="Lich", code="lich", level=30, skill="combat", pos=Position(9, 7), drops=['Drop(code="life_crystal", rate=2000, min_quantity=1, max_quantity=1)', 'Drop(code="lich_crown", rate=600, min_quantity=1, max_quantity=1)']))
    bat: ContentMap = field(default_factory=lambda: ContentMap(name="Bat", code="bat", level=38, skill="combat", pos=Position(8, 9), drops=['Drop(code="bat_wing", rate=12, min_quantity=1, max_quantity=1)']))
    demon: ContentMap = field(default_factory=lambda: ContentMap(name="Demon", code="demon", level=30, skill="combat", pos=Position(-4, 9), drops=['Drop(code="demon_horn", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="piece_of_obsidian", rate=12, min_quantity=1, max_quantity=1)']))
    glowstem: ContentMap = field(default_factory=lambda: ContentMap(name="Glowstem", code="glowstem", level=40, skill="alchemy", pos=Position(1, 10), drops=['Drop(code="glowstem_leaf", rate=1, min_quantity=1, max_quantity=1)']))  
    imp: ContentMap = field(default_factory=lambda: ContentMap(name="Imp", code="imp", level=28, skill="combat", pos=Position(0, 12), drops=['Drop(code="demoniac_dust", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="piece_of_obsidian", rate=70, min_quantity=1, max_quantity=1)']))
    maple_tree: ContentMap = field(default_factory=lambda: ContentMap(name="Maple Tree", code="maple_tree", level=40, skill="woodcutting", pos=Position(1, 12), drops=['Drop(code="maple_wood", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="maple_sap", rate=10, min_quantity=1, max_quantity=1)']))
    bass_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Bass Fishing Spot", code="bass_fishing_spot", level=30, skill="fishing", pos=Position(6, 12), drops=['Drop(code="bass", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)']))
    trout_fishing_spot: ContentMap = field(default_factory=lambda: ContentMap(name="Trout Fishing Spot", code="trout_fishing_spot", level=20, skill="fishing", pos=Position(7, 12), drops=['Drop(code="trout", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="algae", rate=10, min_quantity=1, max_quantity=1)']))
    mithril_rocks: ContentMap = field(default_factory=lambda: ContentMap(name="Mithril Rocks", code="mithril_rocks", level=40, skill="mining", pos=Position(-2, 13), drops=['Drop(code="mithril_ore", rate=1, min_quantity=1, max_quantity=1)', 'Drop(code="topaz_stone", rate=550, min_quantity=1, max_quantity=1)', 'Drop(code="topaz", rate=4500, min_quantity=1, max_quantity=1)', 'Drop(code="emerald", rate=4500, min_quantity=1, max_quantity=1)', 'Drop(code="emerald_stone", rate=550, min_quantity=1, max_quantity=1)', 'Drop(code="ruby", rate=4500, min_quantity=1, max_quantity=1)', 'Drop(code="ruby_stone", rate=550, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire", rate=4500, min_quantity=1, max_quantity=1)', 'Drop(code="sapphire_stone", rate=550, min_quantity=1, max_quantity=1)']))
    hellhound: ContentMap = field(default_factory=lambda: ContentMap(name="Hellhound", code="hellhound", level=40, skill="combat", pos=Position(-1, 13), drops=['Drop(code="hellhound_hair", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="raw_hellhound_meat", rate=10, min_quantity=1, max_quantity=1)', 'Drop(code="hellhound_bone", rate=12, min_quantity=1, max_quantity=1)']))
    cultist_acolyte: ContentMap = field(default_factory=lambda: ContentMap(name="Cultist Acolyte", code="cultist_acolyte", level=33, skill="combat", pos=Position(1, 13), drops=['Drop(code="magic_stone", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="cursed_book", rate=20, min_quantity=1, max_quantity=1)']))
    taskmaster_items: ContentMap = field(default_factory=lambda: ContentMap(name="Cultist Acolyte", code="items", level=33, skill="combat", pos=Position(4, 13), drops=['Drop(code="magic_stone", rate=12, min_quantity=1, max_quantity=1)', 'Drop(code="cursed_book", rate=20, min_quantity=1, max_quantity=1)']))
    nettle: ContentMap = field(default_factory=lambda: ContentMap(name="Nettle", code="nettle", level=20, skill="alchemy", pos=Position(7, 14), drops=['Drop(code="nettle_leaf", rate=1, min_quantity=1, max_quantity=1)']))       


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
        
        Parameters:
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
            "utility2": self.utility2_slot,
            "utility3": self.utility3_slot
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
        
        Parameters:
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

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Account Functions ---
    def get_bank_details(self) -> dict:
        """Retrieve the details of the player's bank account."""
        endpoint = "my/bank"
        return self.api._make_request("GET", endpoint)

    def get_bank_items(self) -> dict:
        """Retrieve the list of items stored in the player's bank."""
        endpoint = "my/bank/items"
        return self.api._make_request("GET", endpoint)

    def get_ge_sell_orders(self) -> dict:
        """Retrieve the player's current sell orders on the Grand Exchange."""
        endpoint = "my/grandexchange/orders"
        return self.api._make_request("GET", endpoint)

    def get_ge_sell_history(self) -> dict:
        """Retrieve the player's Grand Exchange sell history."""
        endpoint = "my/grandexchange/history"
        return self.api._make_request("GET", endpoint)

    def get_account_details(self) -> dict:
        """Retrieve details of the player's account."""
        endpoint = "my/details"
        return self.api._make_request("GET", endpoint)

class Character:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Character Functions ---
    def create_character(self, name: str, skin: str = "men1") -> dict:
        """
        Create a new character with the given name and skin.

        Parameters:
            name (str): The name of the new character.
            skin (str): The skin choice for the character (default is "men1").

        Returns:
            dict: Response data with character creation details.
        """
        endpoint = "characters/create"
        json = {"name": name, "skin": skin}
        return self.api._make_request("POST", endpoint, json=json)

    def delete_character(self, name: str) -> dict:
        """
        Delete a character by name.

        Parameters:
            name (str): The name of the character to delete.

        Returns:
            dict: Response data confirming character deletion.
        """
        endpoint = "characters/delete"
        json = {"name": name}
        return self.api._make_request("POST", endpoint, json=json)

class Actions:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

    # --- Character Actions ---
    def move(self, x: int, y: int) -> dict:
        """
        Move the character to a new position.

        Parameters:
            x (int): X-coordinate to move to.
            y (int): Y-coordinate to move to.

        Returns:
            dict: Response data with updated character position.
        """
        endpoint = f"my/{self.api.char.name}/action/move"
        json = {"x": x, "y": y}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def rest(self) -> dict:
        """
        Perform a rest action to regain energy.

        Returns:
            dict: Response data confirming rest action.
        """
        endpoint = f"my/{self.api.char.name}/action/rest"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    # --- Item Action Functions ---
    def equip_item(self, item_code: str, slot: str, quantity: int = 1) -> dict:
        """
        Equip an item to a specified slot.

        Parameters:
            item_code (str): The code of the item to equip.
            slot (str): The equipment slot.
            quantity (int): The number of items to equip (default is 1).

        Returns:
            dict: Response data with updated equipment.
        """
        endpoint = f"my/{self.api.char.name}/action/equip"
        json = {"code": item_code, "slot": slot, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def unequip_item(self, slot: str, quantity: int = 1) -> dict:
        """
        Unequip an item from a specified slot.

        Parameters:
            slot (str): The equipment slot.
            quantity (int): The number of items to unequip (default is 1).

        Returns:
            dict: Response data with updated equipment.
        """
        endpoint = f"my/{self.api.char.name}/action/unequip"
        json = {"slot": slot, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def use_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Use an item from the player's inventory.

        Parameters:
            item_code (str): Code of the item to use.
            quantity (int): Quantity of the item to use (default is 1).

        Returns:
            dict: Response data confirming the item use.
        """
        endpoint = f"my/{self.api.char.name}/action/use"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def delete_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Delete an item from the player's inventory.

        Parameters:
            item_code (str): Code of the item to delete.
            quantity (int): Quantity of the item to delete (default is 1).

        Returns:
            dict: Response data confirming the item deletion.
        """
        endpoint = f"my/{self.api.char.name}/action/delete-item"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    # --- Resource Action Functions ---
    def fight(self) -> dict:
        """
        Initiate a fight with a monster.

        Returns:
            dict: Response data with fight details.
        """
        endpoint = f"my/{self.api.char.name}/action/fight"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    def gather(self) -> dict:
        """
        Gather resources, such as mining, woodcutting, or fishing.

        Returns:
            dict: Response data with gathered resources.
        """
        endpoint = f"my/{self.api.char.name}/action/gathering"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    def craft_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Craft an item.

        Parameters:
            item_code (str): Code of the item to craft.
            quantity (int): Quantity of the item to craft (default is 1).

        Returns:
            dict: Response data with crafted item details.
        """
        endpoint = f"my/{self.api.char.name}/action/craft"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def recycle_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Recycle an item.

        Parameters:
            item_code (str): Code of the item to recycle.
            quantity (int): Quantity of the item to recycle (default is 1).

        Returns:
            dict: Response data confirming the recycling action.
        """
        endpoint = f"my/{self.api.char.name}/action/recycle"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    # --- Bank Action Functions ---
    def bank_deposit_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Deposit an item into the bank.

        Parameters:
            item_code (str): Code of the item to deposit.
            quantity (int): Quantity of the item to deposit (default is 1).

        Returns:
            dict: Response data confirming the deposit.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/deposit"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def bank_deposit_gold(self, amount: int) -> dict:
        """
        Deposit gold into the bank.

        Parameters:
            amount (int): Amount of gold to deposit.

        Returns:
            dict: Response data confirming the deposit.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/deposit/gold"
        json = {"amount": amount}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def bank_withdraw_item(self, item_code: str, quantity: int = 1) -> dict:
        """
        Withdraw an item from the bank.

        Parameters:
            item_code (str): Code of the item to withdraw.
            quantity (int): Quantity of the item to withdraw (default is 1).

        Returns:
            dict: Response data confirming the withdrawal.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/withdraw"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def bank_withdraw_gold(self, amount: int) -> dict:
        """
        Withdraw gold from the bank.

        Parameters:
            amount (int): Amount of gold to withdraw.

        Returns:
            dict: Response data confirming the withdrawal.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/withdraw/gold"
        json = {"amount": amount}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def bank_buy_expansion(self) -> dict:
        """
        Purchase an expansion for the bank.

        Returns:
            dict: Response data confirming the expansion purchase.
        """
        endpoint = f"my/{self.api.char.name}/action/bank/buy_expansion"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    # --- Grand Exchange Actions Functions ---
    def ge_buy_item(self, order_id: str, quantity: int = 1) -> dict:
        """
        Buy an item from the Grand Exchange.

        Parameters:
            order_id (str): ID of the order to buy from.
            quantity (int): Quantity of the item to buy (default is 1).

        Returns:
            dict: Response data with transaction details.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/buy"
        json = {"id": order_id, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def ge_create_sell_order(self, item_code: str, price: int, quantity: int = 1) -> dict:
        """
        Create a sell order on the Grand Exchange.

        Parameters:
            item_code (str): Code of the item to sell.
            price (int): Selling price per unit.
            quantity (int): Quantity of the item to sell (default is 1).

        Returns:
            dict: Response data confirming the sell order.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/sell"
        json = {"code": item_code, "item_code": price, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def ge_cancel_sell_order(self, order_id: str) -> dict:
        """
        Cancel an active sell order on the Grand Exchange.

        Parameters:
            order_id (str): ID of the order to cancel.

        Returns:
            dict: Response data confirming the order cancellation.
        """
        endpoint = f"my/{self.api.char.name}/action/grandexchange/cancel"
        json = {"id": order_id}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    # --- Taskmaster Action Functions ---
    def taskmaster_accept_task(self) -> dict:
        """
        Accept a new task from the taskmaster.

        Returns:
            dict: Response data confirming task acceptance.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/new"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    def taskmaster_complete_task(self) -> dict:
        """
        Complete the current task with the taskmaster.

        Returns:
            dict: Response data confirming task completion.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/complete"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    def taskmaster_exchange_task(self) -> dict:
        """
        Exchange the current task with the taskmaster.

        Returns:
            dict: Response data confirming task exchange.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/exchange"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

    def taskmaster_trade_task(self, item_code: str, quantity: int = 1) -> dict:
        """
        Trade a task item with another character.

        Parameters:
            item_code (str): Code of the item to trade.
            quantity (int): Quantity of the item to trade (default is 1).

        Returns:
            dict: Response data confirming task trade.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/trade"
        json = {"code": item_code, "quantity": quantity}
        res = self.api._make_request("POST", endpoint, json=json)
        self.api.wait_for_cooldown()
        return res

    def taskmaster_cancel_task(self) -> dict:
        """
        Cancel the current task with the taskmaster.

        Returns:
            dict: Response data confirming task cancellation.
        """
        endpoint = f"my/{self.api.char.name}/action/tasks/cancel"
        res = self.api._make_request("POST", endpoint)
        self.api.wait_for_cooldown()
        return res

class Maps_Functions:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api

        # --- Map Functions ---
    def get_all(self, map_content: Optional[str] = None, content_type: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of maps with optional filters.

        Parameters:
            map_content (Optional[str]): Filter maps by specific content.
            content_type (Optional[str]): Filter maps by content type.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of maps.
        """
        query = "size=100"
        if map_content:
            query += f"&code_content={map_content}"
        if content_type:
            query += f"&content_type={content_type}"
        query += f"&page={page}"
        endpoint = f"maps?{query}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_map(self, x: int, y: int) -> dict:
        """
        Retrieve map data for a specific coordinate.

        Parameters:
            x (int): X-coordinate of the map.
            y (int): Y-coordinate of the map.

        Returns:
            dict: Response data for the specified map.
        """
        endpoint = f"maps/{x}/{y}"
        return self.api._make_request("GET", endpoint).get("data")

class Items:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
        # --- Item Functions ---
    def get_all(
        self, craft_material: Optional[str] = None, craft_skill: Optional[str] = None, max_level: Optional[int] = None,
        min_level: Optional[int] = None, name: Optional[str] = None, item_type: Optional[str] = None, page: int = 1
    ) -> dict:
        """
        Retrieve a list of items with optional filters.

        Parameters:
            craft_material (Optional[str]): Filter items by crafting material.
            craft_skill (Optional[str]): Filter items by crafting skill.
            max_level (Optional[int]): Maximum level for the items.
            min_level (Optional[int]): Minimum level for the items.
            name (Optional[str]): Filter items by name.
            item_type (Optional[str]): Filter items by type.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of items.
        """
        query = "size=100"
        if craft_material:
            query += f"&craft_material={craft_material}"
        if craft_skill:
            query += f"&craft_skill={craft_skill}"
        if max_level:
            query += f"&max_level={max_level}"
        if min_level:
            query += f"&min_level={min_level}"
        if name:
            query += f"&name={name}"
        if page:
            query += f"&page={page}"
        if item_type:
            query += f"&item_type={item_type}"
        endpoint = f"items?{query}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_item(self, item_code: str) -> dict:
        """
        Retrieve details for a specific item.

        Parameters:
            item_code (str): Code of the item.

        Returns:
            dict: Response data for the specified item.
        """
        endpoint = f"items/{item_code}"
        return self.api._make_request("GET", endpoint).get("data")

class Monsters:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Monster Functions ---
    def get_all(self, drop: Optional[str] = None, max_level: Optional[int] = None, min_level: Optional[int] = None, page: int = 1) -> dict:
        """
        Retrieve a list of monsters with optional filters.

        Parameters:
            drop (Optional[str]): Filter monsters by drop item.
            max_level (Optional[int]): Maximum level for the monsters.
            min_level (Optional[int]): Minimum level for the monsters.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of monsters.
        """
        query = "size=100"
        if max_level:
            query += f"&max_level={max_level}"
        if min_level:
            query += f"&min_level={min_level}"
        if drop:
            query += f"&drop={drop}"
        if page:
            query += f"&page={page}"
        endpoint = f"monsters?{query}"
        return self.api._make_request("GET", endpoint).get("data")
    
    def get_monster(self, monster_code: str) -> dict:
        """
        Retrieve details for a specific monster.

        Parameters:
            monster_code (str): Code of the monster.

        Returns:
            dict: Response data for the specified monster.
        """
        endpoint = f"monsters/{monster_code}"
        return self.api._make_request("GET", endpoint).get("data")

class Resources:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Resource Functions ---
    def get_all(self, drop: Optional[str] = None, max_level: Optional[int] = None, min_level: Optional[int] = None, skill: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of resources with optional filters.

        Parameters:
            drop (Optional[str]): Filter resources by drop item.
            max_level (Optional[int]): Maximum level for the resources.
            min_level (Optional[int]): Minimum level for the resources.
            skill (Optional[str]): Filter resources by skill required.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of resources.
        """
        query = "size=100"
        if max_level:
            query += f"&max_level={max_level}"
        if min_level:
            query += f"&min_level={min_level}"
        if drop:
            query += f"&drop={drop}"
        if skill:
            query += f"&skill={skill}"
        if page:
            query += f"&page={page}"
        endpoint = f"resources?{query}"
        return self.api._make_request("GET", endpoint).get("data")
    
    def get_resource(self, resource_code: str) -> dict:
        """
        Retrieve details for a specific resource.

        Parameters:
            resource_code (str): Code of the resource.

        Returns:
            dict: Response data for the specified resource.
        """
        endpoint = f"resources/{resource_code}"
        return self.api._make_request("GET", endpoint).get("data")

class Events:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Event Functions ---
    def get_active(self, page: int = 1) -> dict:
        """
        Retrieve a list of active events.

        Parameters:
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of active events.
        """
        query = f"size=100&page={page}"
        endpoint = f"events/active?{query}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_all(self, page: int = 1) -> dict:
        """
        Retrieve a list of all events.

        Parameters:
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with a list of events.
        """
        query = f"size=100&page={page}"
        endpoint = f"events?{query}"
        return self.api._make_request("GET", endpoint).get("data")

class GE:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Grand Exchange Functions ---
    def get_history(self, item_code: str, buyer: Optional[str] = None, seller: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the transaction history for a specific item on the Grand Exchange.

        Parameters:
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
        return self.api._make_request("GET", endpoint).get("data")

    def get_sell_orders(self, item_code: Optional[str] = None, seller: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of sell orders on the Grand Exchange with optional filters.

        Parameters:
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
        return self.api._make_request("GET", endpoint).get("data")

    def get_sell_order(self, order_id: str) -> dict:
        """
        Retrieve details for a specific sell order on the Grand Exchange.

        Parameters:
            order_id (str): ID of the order.

        Returns:
            dict: Response data for the specified sell order.
        """
        endpoint = f"grandexchange/orders/{order_id}"
        return self.api._make_request("GET", endpoint).get("data")

class Tasks:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Task Functions ---
    def get_all(self, skill: Optional[str] = None, task_type: Optional[str] = None, max_level: Optional[int] = None, min_level: Optional[int] = None, page: int = 1) -> dict:
        """
        Retrieve a list of tasks with optional filters.

        Parameters:
            skill (Optional[str]): Filter tasks by skill.
            task_type (Optional[str]): Filter tasks by type.
            max_level (Optional[int]): Maximum level for the tasks.
            min_level (Optional[int]): Minimum level for the tasks.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of tasks.
        """
        query = "size=100"
        if max_level:
            query += f"&max_level={max_level}"
        if min_level:
            query += f"&min_level={min_level}"
        if task_type:
            query += f"&task_type={task_type}"
        if skill:
            query += f"&skill={skill}"
        if page:
            query += f"&page={page}"
        endpoint = f"tasks/list?{query}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_task(self, task_code: str) -> dict:
        """
        Retrieve details for a specific task.

        Parameters:
            task_code (str): Code of the task.

        Returns:
            dict: Response data for the specified task.
        """
        endpoint = f"tasks/list/{task_code}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_all_rewards(self, page: int = 1) -> dict:
        """
        Retrieve a list of task rewards.

        Parameters:
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of task rewards.
        """
        query = f"size=100&page={page}"    
        endpoint = f"tasks/rewards?{query}"
        return self.api._make_request("GET", endpoint).get("data")

    def get_reward(self, task_code: str) -> dict:
        """
        Retrieve details for a specific task reward.

        Parameters:
            task_code (str): Code of the task reward.

        Returns:
            dict: Response data for the specified task reward.
        """
        endpoint = f"tasks/rewards/{task_code}"
        return self.api._make_request("GET", endpoint).get("data")

class Achievements:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Achievement Functions ---
    def get_all(self, achievement_type: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of achievements with optional filters.

        Parameters:
            achievement_type (Optional[str]): Filter achievements by type.
            page (int): Pagination page number (default is 1).

        Returns:
            dict: Response data with the list of achievements.
        """
        query = "size=100"
        if achievement_type:
            query += f"&achievement_type={achievement_type}"
        query += f"&page={page}"
        endpoint = f"achievements?{query}"
        return self.api._make_request("GET", endpoint).get("data")
    
    def get_achievement(self, achievement_code: str) -> dict:
        """
        Retrieve details for a specific achievement.

        Parameters:
            achievement_code (str): Code of the achievement.

        Returns:
            dict: Response data for the specified achievement.
        """
        endpoint = f"achievements/{achievement_code}"
        return self.api._make_request("GET", endpoint).get("data")

class Leaderboard:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Leaderboard Functions ---
    def get_characters_leaderboard(self, sort: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the characters leaderboard with optional sorting.

        Parameters:
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
        return self.api._make_request("GET", endpoint)

    def get_accounts_leaderboard(self, sort: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve the accounts leaderboard with optional sorting.

        Parameters:
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
        return self.api._make_request("GET", endpoint)

class Accounts:
    def __init__(self, api: "ArtifactsAPI"):
        """
        Initialize with a reference to the main API to access shared methods.

        Parameters:
            api (ArtifactsAPI): Instance of the main API class.
        """
        self.api = api
    # --- Accounts Functions ---
    def get_account_achievements(self, account: str, completed: Optional[bool] = None, achievement_type: Optional[str] = None, page: int = 1) -> dict:
        """
        Retrieve a list of achievements for a specific account with optional filters.

        Parameters:
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
        return self.api._make_request("GET", endpoint) 



# --- Wrapper ---
class ArtifactsAPI:
    """
    Wrapper class for interacting with the Artifacts MMO API.
    
    Attributes:
        token (str): The API token for authenticating requests.
        base_url (str): The base URL of the API.
        headers (dict): The headers to include in each request.
        character (PlayerData): The player character associated with this instance.
    """
    def __init__(self, api_key: str, character_name: str):
        """
        Initialize the API wrapper with an API key and character name.

        Parameters:
            api_key (str): API key for authorization.
            character_name (str): Name of the character to retrieve and interact with.
        """
        self.token: str = api_key
        self.base_url: str = "https://api.artifactsmmo.com"
        self.headers: Dict[str, str] = {
            "content-type": "application/json",
            "Accept": "application/json",
            "Authorization": f'Bearer {self.token}'
        }
        self.char: PlayerData = self.get_character(character_name=character_name)

        # --- Subclass definition ---
        self.account = Account(self)
        self.character = Character(self)
        self.actions = Actions(self)
        self.maps = Maps_Functions(self)
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

    def _make_request(self, method: str, endpoint: str, json: Optional[dict] = None, source: Optional[str] = None) -> dict:
        """
        Makes an API request and returns the JSON response.

        Parameters:
            method (str): HTTP method (e.g., "GET", "POST").
            endpoint (str): API endpoint to send the request to.
            json (Optional[dict]): JSON data to include in the request body.
            source (Optional[str]): Source of the request for conditional handling.

        Returns:
            dict: The JSON response from the API.
        
        Raises:
            APIException: For various HTTP status codes with relevant error messages.
        """
        try:
            endpoint = endpoint.strip("/")
            if debug and source != "get_character":
                self._print(endpoint)
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(method, url, headers=self.headers, json=json)
        except Exception as e:
            self._print(e)
            self._make_request(method, endpoint, json, source)

        if response.status_code != 200:
            message = f"An error occurred. Returned code {response.status_code}, {response.json().get('error', {}).get('message', '')}, {endpoint}"
            self._raise(response.status_code, message)

        if source != "get_character":
            self.get_character()
            
        return response.json()

    def _print(self, message: Union[str, Exception]) -> None:
        """
        Prints a message with a timestamp and character name.

        Parameters:
            message (Union[str, Exception]): The message or exception to print.
        """
        m = f"[{self.char.name}] {datetime.now().strftime('%H:%M:%S')} - {message}"
        print(m)

    def _raise(self, code: int, message: str) -> None:
        """
        Raises an API exception based on the response code and error message.

        Parameters:
            code (int): HTTP status code.
            message (str): Error message.

        Raises:
            Exception: Corresponding exception based on the code provided.
        """
        m = f"[{self.char.name}] {datetime.now().strftime('%H:%M:%S')} - {message}"
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
                self._print(m)
            case 452:
                raise APIException.TokenMissingorEmpty(m)
        if code != 200 and code != 490:
            raise Exception(m)


    # --- Helper Functions ---
    def wait_for_cooldown(self) -> None:
        """
        Wait for the character's cooldown time to expire, if applicable.
        
        This function prints the cooldown time remaining and pauses
        execution until it has expired.
        """
        cooldown_time = self.char.cooldown
        if cooldown_time > 0:
            self._print(f"Waiting for cooldown... ({cooldown_time} seconds)")
            time.sleep(cooldown_time)

    def get_character(self, data: Optional[dict] = None, character_name: Optional[str] = None) -> PlayerData:
        """
        Retrieve or update the character's data and initialize the character attribute.

        Parameters:
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
    

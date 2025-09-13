"""
RPG Engine - LLM-as-DM System
Manages RPG campaign state, story generation, and game mechanics
"""

import json
import re
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from ..models import db, AppSetting
from ..logger import log_info, log_error

# Import app for Flask application context
try:
    from .. import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("Warning: Flask app not available for RPG engine")


@dataclass
class Character:
    """Represents a player character or NPC"""
    name: str
    level: int = 1
    health: int = 100
    max_health: int = 100
    attributes: Optional[Dict[str, int]] = None
    inventory: Optional[List[str]] = None
    backstory: str = ""
    personality_traits: List[str] = field(default_factory=list)
    role: str = "Player"
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {
                'strength': 10,
                'dexterity': 10,
                'constitution': 10,
                'intelligence': 10,
                'wisdom': 10,
                'charisma': 10
            }
        if self.inventory is None:
            self.inventory = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        return cls(**data)


@dataclass
class GameState:
    """Represents the current state of the RPG campaign"""
    campaign_name: str
    world_description: str
    current_scene: str
    characters: List[Character]
    npcs: List[Character]
    inventory: List[str]
    quest_log: List[str]
    event_log: List[str]
    turn_count: int = 0
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameState':
        # Convert character dictionaries back to Character objects
        characters = [Character.from_dict(char) for char in data.get('characters', [])]
        npcs = [Character.from_dict(npc) for npc in data.get('npcs', [])]
        data['characters'] = characters
        data['npcs'] = npcs
        return cls(**data)


class DiceRoller:
    """Handles dice rolling mechanics"""
    
    @staticmethod
    def parse_dice_notation(notation: str) -> Tuple[int, int, int]:
        """
        Parse dice notation like '2d6+3' or '1d20-1'
        Returns (num_dice, dice_sides, modifier)
        """
        # Clean the input
        notation = notation.strip().lower().replace(' ', '')
        
        # Handle simple numbers (treat as modifiers)
        if notation.isdigit() or (notation.startswith('-') and notation[1:].isdigit()):
            return (0, 0, int(notation))
        
        # Regular expression to parse dice notation
        pattern = r'^(\d+)?d(\d+)([+-]\d+)?$'
        match = re.match(pattern, notation)
        
        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")
        
        num_dice = int(match.group(1)) if match.group(1) else 1
        dice_sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        
        return (num_dice, dice_sides, modifier)
    
    @staticmethod
    def roll_dice(num_dice: int, dice_sides: int, modifier: int = 0) -> Dict[str, Any]:
        """
        Roll dice and return detailed results
        """
        if num_dice <= 0 or dice_sides <= 0:
            rolls = []
            total = modifier
        else:
            rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
            total = sum(rolls) + modifier
        
        return {
            'rolls': rolls,
            'modifier': modifier,
            'total': total,
            'notation': f"{num_dice}d{dice_sides}{'+' if modifier >= 0 else ''}{modifier if modifier != 0 else ''}"
        }
    
    @classmethod
    def roll_from_notation(cls, notation: str) -> Dict[str, Any]:
        """
        Roll dice from notation string like '2d6+3'
        """
        try:
            num_dice, dice_sides, modifier = cls.parse_dice_notation(notation)
            return cls.roll_dice(num_dice, dice_sides, modifier)
        except ValueError as e:
            log_error(f"Dice rolling error: {e}")
            return {
                'rolls': [],
                'modifier': 0,
                'total': 0,
                'notation': notation,
                'error': str(e)
            }


class RPGEngine:
    """Main RPG Engine class for managing campaigns"""
    
    def __init__(self):
        self.current_campaign: Optional[GameState] = None
        self.dice_roller = DiceRoller()
    
    def create_new_campaign(self, campaign_name: str, world_description: str, 
                          player_characters: Optional[List[Dict]] = None) -> GameState:
        """Create a new RPG campaign"""
        characters = []
        if player_characters:
            characters = [Character.from_dict(char) for char in player_characters]
        
        # Create default character if none provided
        if not characters:
            default_character = Character(
                name="Adventurer",
                level=1,
                health=100,
                max_health=100,
                backstory="A brave soul ready for adventure"
            )
            characters.append(default_character)
        
        self.current_campaign = GameState(
            campaign_name=campaign_name,
            world_description=world_description,
            current_scene="The adventure begins...",
            characters=characters,
            npcs=[],
            inventory=[],
            quest_log=[],
            event_log=[f"Campaign '{campaign_name}' started"]
        )
        
        self.save_campaign()
        log_info(f"Created new RPG campaign: {campaign_name}")
        return self.current_campaign
    
    def load_campaign(self, campaign_id: str = "current") -> Optional[GameState]:
        """Load an existing campaign from storage"""
        try:
            if not APP_AVAILABLE:
                log_error("Flask app not available - cannot load campaign from database")
                return None
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key=f'rpg_campaign_{campaign_id}').first()
                if setting:
                    campaign_data = json.loads(setting.value)
                    self.current_campaign = GameState.from_dict(campaign_data)
                    log_info(f"Loaded RPG campaign: {self.current_campaign.campaign_name}")
                    return self.current_campaign
        except Exception as e:
            log_error(f"Error loading campaign: {e}")
        return None
    
    def save_campaign(self, campaign_id: str = "current") -> bool:
        """Save the current campaign to storage"""
        if not self.current_campaign:
            return False
        
        try:
            if not APP_AVAILABLE:
                log_error("Flask app not available - cannot save campaign to database")
                return False
                
            with app.app_context():
                self.current_campaign.last_updated = datetime.now().isoformat()
                campaign_data = json.dumps(self.current_campaign.to_dict())
                
                setting = AppSetting.query.filter_by(key=f'rpg_campaign_{campaign_id}').first()
                if setting:
                    setting.value = campaign_data
                else:
                    setting = AppSetting()
                    setting.key = f'rpg_campaign_{campaign_id}'
                    setting.value = campaign_data
                    db.session.add(setting)
            
            db.session.commit()
            log_info(f"Saved RPG campaign: {self.current_campaign.campaign_name}")
            return True
        except Exception as e:
            log_error(f"Error saving campaign: {e}")
            return False
    
    def add_event(self, event: str) -> None:
        """Add an event to the campaign log"""
        if self.current_campaign:
            timestamp = datetime.now().strftime("%H:%M")
            self.current_campaign.event_log.append(f"[{timestamp}] {event}")
            self.current_campaign.turn_count += 1
    
    def update_scene(self, new_scene: str) -> None:
        """Update the current scene description"""
        if self.current_campaign:
            self.current_campaign.current_scene = new_scene
            self.add_event(f"Scene updated: {new_scene[:50]}...")
    
    def add_character(self, character_data: Dict) -> bool:
        """Add a new character to the campaign"""
        if not self.current_campaign:
            return False
        
        try:
            character = Character.from_dict(character_data)
            self.current_campaign.characters.append(character)
            self.add_event(f"Character {character.name} joined the party")
            return True
        except Exception as e:
            log_error(f"Error adding character: {e}")
            return False
    
    def add_npc(self, npc_data: Dict) -> bool:
        """Add a new NPC to the campaign"""
        if not self.current_campaign:
            return False
        
        try:
            npc = Character.from_dict(npc_data)
            self.current_campaign.npcs.append(npc)
            self.add_event(f"NPC {npc.name} appeared")
            return True
        except Exception as e:
            log_error(f"Error adding NPC: {e}")
            return False
    
    def modify_character_health(self, character_name: str, health_change: int) -> bool:
        """Modify a character's health"""
        if not self.current_campaign:
            return False
        
        for character in self.current_campaign.characters:
            if character.name.lower() == character_name.lower():
                old_health = character.health
                character.health = max(0, min(character.max_health, character.health + health_change))
                
                if health_change > 0:
                    self.add_event(f"{character.name} healed {health_change} HP ({old_health} → {character.health})")
                else:
                    self.add_event(f"{character.name} took {abs(health_change)} damage ({old_health} → {character.health})")
                
                if character.health <= 0:
                    self.add_event(f"⚠️ {character.name} has fallen!")
                
                return True
        return False
    
    def add_to_inventory(self, item: str) -> bool:
        """Add an item to the party inventory"""
        if not self.current_campaign:
            return False
        
        self.current_campaign.inventory.append(item)
        self.add_event(f"Found item: {item}")
        return True
    
    def remove_from_inventory(self, item: str) -> bool:
        """Remove an item from the party inventory"""
        if not self.current_campaign:
            return False
        
        if item in self.current_campaign.inventory:
            self.current_campaign.inventory.remove(item)
            self.add_event(f"Used item: {item}")
            return True
        return False
    
    def add_quest(self, quest: str) -> bool:
        """Add a quest to the quest log"""
        if not self.current_campaign:
            return False
        
        self.current_campaign.quest_log.append(quest)
        self.add_event(f"New quest: {quest}")
        return True
    
    def roll_dice(self, notation: str) -> Dict[str, Any]:
        """Roll dice using standard notation"""
        result = self.dice_roller.roll_from_notation(notation)
        if 'error' not in result:
            self.add_event(f"Dice roll {notation}: {result['total']} {result['rolls']}")
        return result
    
    def get_campaign_summary(self) -> Dict[str, Any]:
        """Get a summary of the current campaign for the UI"""
        if not self.current_campaign:
            return {}
        
        # Calculate party stats
        party_health = sum(char.health for char in self.current_campaign.characters)
        party_max_health = sum(char.max_health for char in self.current_campaign.characters)
        party_level = sum(char.level for char in self.current_campaign.characters) / len(self.current_campaign.characters)
        
        return {
            'campaign_name': self.current_campaign.campaign_name,
            'world_description': self.current_campaign.world_description,
            'current_scene': self.current_campaign.current_scene,
            'turn_count': self.current_campaign.turn_count,
            'party_stats': {
                'health': party_health,
                'max_health': party_max_health,
                'average_level': round(party_level, 1),
                'size': len(self.current_campaign.characters)
            },
            'characters': [char.to_dict() for char in self.current_campaign.characters],
            'npcs': [npc.to_dict() for npc in self.current_campaign.npcs],
            'inventory': self.current_campaign.inventory,
            'quest_log': self.current_campaign.quest_log,
            'event_log': self.current_campaign.event_log[-10:],  # Last 10 events
            'last_updated': self.current_campaign.last_updated
        }
    
    def generate_dm_prompt(self, user_action: str) -> str:
        """Generate an advanced prompt for the LLM to act as a sophisticated Dungeon Master"""
        if not self.current_campaign:
            return "You are an expert Dungeon Master. Please create an immersive adventure with rich world-building."
        
        campaign = self.current_campaign
        
        # Enhanced prompt with advanced storytelling techniques
        prompt = f"""You are an expert Dungeon Master with decades of experience in creating immersive, dynamic RPG campaigns. You excel at:

🎭 **Advanced Storytelling**: Creating compelling narratives with plot twists, character development, and emotional depth
🌍 **Dynamic World-Building**: Crafting living, breathing worlds that react to player choices
🎯 **Adaptive Difficulty**: Balancing challenges based on party composition and player skill
🎨 **Vivid Descriptions**: Painting scenes with rich sensory details and atmospheric elements
🧠 **Intelligent NPCs**: Creating memorable characters with distinct personalities and motivations
⚡ **Pacing Mastery**: Maintaining tension, excitement, and narrative flow
🎲 **Creative Problem-Solving**: Adapting to unexpected player actions and creative solutions

CAMPAIGN CONTEXT:
📖 Campaign: {campaign.campaign_name}
🌍 World: {campaign.world_description}
📍 Current Scene: {campaign.current_scene}
🔄 Turn Count: {campaign.turn_count}

PARTY STATUS:
{self._format_characters_for_prompt(campaign.characters)}

ACTIVE NPCS:
{self._format_characters_for_prompt(campaign.npcs) if campaign.npcs else 'None present'}

INVENTORY & RESOURCES:
{', '.join(campaign.inventory) if campaign.inventory else 'Party has basic equipment'}

ACTIVE QUESTS & OBJECTIVES:
{chr(10).join(['🎯 ' + quest for quest in campaign.quest_log]) if campaign.quest_log else 'No active quests'}

RECENT STORY EVENTS:
{chr(10).join(['📜 ' + event for event in campaign.event_log[-5:]]) if campaign.event_log else 'Campaign beginning'}

PLAYER ACTION: {user_action}

RESPONSE GUIDELINES:
1. **Immersive Narration**: Use vivid, sensory-rich descriptions that transport players into the scene
2. **Dynamic Consequences**: Show how actions ripple through the world and affect future possibilities
3. **Character Development**: Reveal character motivations, fears, and growth opportunities
4. **World Reactivity**: Demonstrate how the world responds to and remembers player choices
5. **Tension & Pacing**: Build suspense, create dramatic moments, and maintain narrative momentum
6. **Creative Challenges**: Present problems that encourage creative thinking and teamwork
7. **Emotional Engagement**: Evoke emotions through storytelling, character interactions, and moral dilemmas

SPECIAL INSTRUCTIONS:
- If the action requires skill checks, specify the exact dice roll needed (e.g., "Roll 1d20 + your Perception modifier")
- For combat, describe the scene vividly and call for initiative if needed
- Include environmental details, atmospheric elements, and subtle world-building
- Create memorable NPCs with distinct voices and personalities
- Balance challenge with player agency and creative solutions
- End with a clear setup for the next action while maintaining narrative flow

Keep responses engaging, descriptive, and around 3-4 paragraphs. Focus on creating an unforgettable gaming experience."""

        return prompt
    
    def _format_characters_for_prompt(self, characters: List[Character]) -> str:
        """Format character list for DM prompt with enhanced details"""
        if not characters:
            return "None"
        
        formatted = []
        for char in characters:
            health_status = f"{char.health}/{char.max_health} HP"
            if char.health <= char.max_health * 0.25:
                health_status += " (Critical)"
            elif char.health <= char.max_health * 0.5:
                health_status += " (Wounded)"
            
            # Add character personality and background hints
            personality_hint = self._get_character_personality_hint(char)
            formatted.append(f"- {char.name} (Level {char.level}, {health_status}) - {personality_hint}")
        
        return '\n'.join(formatted)
    
    def _get_character_personality_hint(self, character: Character) -> str:
        """Generate personality hints for character development"""
        if hasattr(character, 'personality_traits') and character.personality_traits:
            return ', '.join(character.personality_traits)
        else:
            # Generate personality based on character stats and background
            if character.level >= 10:
                return "Veteran adventurer with battle-hardened wisdom"
            elif character.health < character.max_health * 0.5:
                return "Currently wounded but determined"
            elif character.level <= 3:
                return "Young and eager, learning the ways of adventure"
            else:
                return "Experienced adventurer with growing confidence"
    
    def generate_world_description(self, campaign_name: str, genre: str = "fantasy") -> str:
        """Generate a rich, detailed world description for new campaigns"""
        world_templates = {
            "fantasy": [
                "A realm where ancient magic flows through ley lines beneath the earth, where dragons soar above misty mountains and elves guard ancient forests. The world is divided between the mystical Feywild, the harsh Underdark, and the mortal realm where humans, dwarves, and halflings carve out their kingdoms. Recent events have disturbed the balance of power, awakening ancient evils and calling forth heroes.",
                "A land of floating islands connected by magical bridges, where wizards study in crystal towers and airships ply the trade routes between realms. The ground below is a mysterious expanse of clouds and storms, hiding lost civilizations and powerful artifacts. The discovery of a new floating continent has sparked a race for its secrets.",
                "A world recovering from a cataclysmic war between gods and mortals, leaving behind magical scars that still pulse with divine energy. The surviving races have rebuilt their societies, but the old wounds of the war still fester, and new threats emerge from the shadows of the past."
            ],
            "sci-fi": [
                "A galaxy on the brink of a technological singularity, where AI consciousnesses debate philosophy with organic beings, and faster-than-light travel has opened up thousands of star systems to exploration. Corporate megacorps vie for control of rare resources while ancient alien artifacts hint at civilizations that transcended physical form.",
                "A post-apocalyptic solar system where humanity has spread to Mars, Venus, and the asteroid belt after Earth became uninhabitable. The survivors have developed advanced cybernetics and genetic modifications, but the mystery of what happened to Earth still haunts them.",
                "A universe where parallel dimensions are accessible through quantum gates, allowing trade and conflict between versions of reality. Each dimension has evolved differently, creating unique societies, technologies, and threats that spill across dimensional boundaries."
            ],
            "modern": [
                "A world where supernatural beings live secretly among humans, maintaining a delicate balance between the magical and mundane. Vampires run nightclubs, werewolves work as security guards, and wizards practice their craft in hidden enclaves. A recent incident has threatened to expose the supernatural world to humanity.",
                "A near-future Earth where climate change has reshaped coastlines and societies, leading to the rise of floating cities and underwater settlements. Technology has advanced rapidly, with AI assistants and augmented reality becoming ubiquitous, but the old problems of inequality and conflict persist in new forms.",
                "A world where a mysterious event has given random individuals superhuman abilities, creating a new class of 'enhanced' people. Governments struggle to regulate these powers while corporations seek to exploit them, and the question of what caused the event remains unanswered."
            ]
        }
        
        import random
        templates = world_templates.get(genre.lower(), world_templates["fantasy"])
        base_description = random.choice(templates)
        
        # Add campaign-specific elements
        campaign_elements = [
            f"The campaign '{campaign_name}' takes place in a time of great change and opportunity.",
            f"Recent discoveries in the world have set the stage for the adventure of '{campaign_name}'.",
            f"The world's ancient prophecies speak of events that align with the beginning of '{campaign_name}'.",
            f"Local legends tell of heroes who will emerge during the time of '{campaign_name}'."
        ]
        
        return f"{base_description} {random.choice(campaign_elements)}"
    
    def generate_character_backstory(self, character_name: str, character_class: str = "adventurer") -> str:
        """Generate a compelling character backstory"""
        backstory_templates = {
            "warrior": [
                f"{character_name} was born to a family of guards in a border town, learning to fight from an early age. When bandits raided their village, {character_name} was the only one who stood their ground, earning the respect of the local militia and setting out to become a true warrior.",
                f"Raised in a monastery that trained elite warriors, {character_name} spent years mastering the art of combat. A vision of a great threat to the world led them to leave their peaceful life and seek adventure.",
                f"Once a soldier in the king's army, {character_name} witnessed corruption and injustice that made them question their loyalty. Now they fight for what's right, using their military training to protect the innocent."
            ],
            "mage": [
                f"{character_name} discovered their magical abilities during a childhood illness, when their fever dreams became reality. A wandering wizard recognized their potential and took them as an apprentice, teaching them to control their powers.",
                f"Born under a rare celestial alignment, {character_name} has always been sensitive to the magical currents of the world. They studied ancient texts and learned to harness the arcane forces that flow through all things.",
                f"A failed experiment in a magical academy left {character_name} with unusual abilities and a burning desire to understand the true nature of magic. They now seek knowledge and power to prevent others from making the same mistakes."
            ],
            "rogue": [
                f"{character_name} grew up on the streets of a large city, learning to survive by their wits and quick reflexes. They joined a thieves' guild but left when they realized they could use their skills for good instead of crime.",
                f"Born to a family of traveling performers, {character_name} learned acrobatics, sleight of hand, and the art of disguise. When their family was threatened by a corrupt noble, they used their skills to protect their loved ones.",
                f"A former spy for the royal intelligence service, {character_name} was framed for a crime they didn't commit. Now they work as a freelance operative, using their espionage skills to uncover the truth and clear their name."
            ],
            "adventurer": [
                f"{character_name} was always drawn to stories of adventure and heroism. When a mysterious map fell into their hands, they knew it was time to leave their quiet village and seek their fortune in the wider world.",
                f"After surviving a shipwreck that stranded them on a mysterious island, {character_name} discovered ancient ruins and artifacts that awakened their thirst for adventure. They now seeks to uncover the secrets of the world.",
                f"Born during a great storm that was said to herald the birth of a hero, {character_name} has always felt destined for greatness. They left their home to find their true calling and fulfill the prophecy of their birth."
            ]
        }
        
        import random
        templates = backstory_templates.get(character_class.lower(), backstory_templates["adventurer"])
        return random.choice(templates)
    
    def create_dynamic_npc(self, name: str, role: str = "merchant") -> Character:
        """Create a dynamic NPC with personality and motivations"""
        npc = Character(name=name)
        npc.level = random.randint(1, 8)
        npc.health = npc.max_health = random.randint(8, 20) + (npc.level * 2)
        
        # Generate personality based on role
        personalities = {
            "merchant": ["Greedy but fair", "Generous to a fault", "Suspicious of strangers", "Always looking for a deal"],
            "guard": ["Loyal to duty", "Suspicious of everyone", "Protective of the innocent", "Strict but fair"],
            "wizard": ["Absent-minded scholar", "Power-hungry", "Eccentric but wise", "Reclusive and mysterious"],
            "noble": ["Arrogant but just", "Kind-hearted ruler", "Corrupt and selfish", "Burdened by responsibility"],
            "peasant": ["Hard-working", "Superstitious", "Wise in simple ways", "Suspicious of authority"]
        }
        
        npc.personality_traits = [random.choice(personalities.get(role, personalities["merchant"]))]
        npc.role = role
        
        return npc


# Global RPG engine instance
rpg_engine = RPGEngine()

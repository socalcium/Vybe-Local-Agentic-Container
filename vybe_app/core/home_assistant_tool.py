"""
Home Assistant Manager Tool
==========================
Tool integration for the Manager Model to control smart home devices
"""

import json
import logging
from typing import Dict, Any, Optional
from vybe_app.api.home_assistant_api import handle_home_assistant_tool, ha_connection

logger = logging.getLogger(__name__)


class HomeAssistantTool:
    """Home Assistant tool for Manager Model integration"""
    
    def __init__(self):
        self.name = "HOME_ASSISTANT"
        self.description = """Control Home Assistant smart home devices. 
        
        Examples:
        - Turn on lights: [TOOL:HOME_ASSISTANT service=light.turn_on entity_id=light.living_room]
        - Turn off switches: [TOOL:HOME_ASSISTANT service=switch.turn_off entity_id=switch.bedroom_fan]
        - Toggle devices: [TOOL:HOME_ASSISTANT service=light.toggle entity_id=light.kitchen]
        - Set brightness: [TOOL:HOME_ASSISTANT service=light.turn_on entity_id=light.bedroom brightness=128]
        - Set color: [TOOL:HOME_ASSISTANT service=light.turn_on entity_id=light.living_room rgb_color=[255,0,0]]
        
        Common services:
        - light.turn_on, light.turn_off, light.toggle
        - switch.turn_on, switch.turn_off, switch.toggle  
        - cover.open_cover, cover.close_cover, cover.toggle
        - climate.set_temperature, climate.set_hvac_mode
        - media_player.play_media, media_player.pause, media_player.volume_set
        """
    
    def execute(self, service: str, entity_id: str, **kwargs) -> Dict[str, Any]:
        """Execute a Home Assistant service call"""
        try:
            # Remove None values and prepare service_data
            service_data = {k: v for k, v in kwargs.items() if v is not None}
            
            # Handle special parameters
            if 'brightness' in service_data:
                # Ensure brightness is an integer between 0-255
                try:
                    service_data['brightness'] = max(0, min(255, int(service_data['brightness'])))
                except (ValueError, TypeError):
                    return {
                        'success': False,
                        'message': f'Invalid brightness value: {service_data["brightness"]}'
                    }
            
            if 'rgb_color' in service_data:
                # Ensure RGB color is a list of 3 integers
                try:
                    rgb = service_data['rgb_color']
                    if isinstance(rgb, str):
                        # Parse string representation like "[255,0,0]"
                        rgb = json.loads(rgb)
                    if not isinstance(rgb, list) or len(rgb) != 3:
                        raise ValueError("RGB color must be a list of 3 values")
                    service_data['rgb_color'] = [max(0, min(255, int(c))) for c in rgb]
                except (ValueError, TypeError, json.JSONDecodeError):
                    return {
                        'success': False,
                        'message': f'Invalid RGB color format: {service_data["rgb_color"]}'
                    }
            
            if 'temperature' in service_data:
                # Ensure temperature is a number
                try:
                    service_data['temperature'] = float(service_data['temperature'])
                except (ValueError, TypeError):
                    return {
                        'success': False,
                        'message': f'Invalid temperature value: {service_data["temperature"]}'
                    }
            
            # Call the Home Assistant API
            result = handle_home_assistant_tool(service, entity_id, service_data if service_data else None)
            
            if result['success']:
                logger.info(f"Home Assistant service call successful: {service} on {entity_id}")
            else:
                logger.warning(f"Home Assistant service call failed: {result['message']}")
            
            return result
            
        except Exception as e:
            error_msg = f"Home Assistant tool error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def get_available_devices(self) -> Dict[str, Any]:
        """Get list of available devices for the Manager Model"""
        if not ha_connection['connected']:
            return {
                'success': False,
                'message': 'Home Assistant not connected',
                'devices': []
            }
        
        try:
            devices = ha_connection.get('devices', [])
            
            # Format devices for Manager Model consumption
            device_list = []
            for device in devices:
                device_info = {
                    'entity_id': device['entity_id'],
                    'name': device['name'],
                    'domain': device['domain'],
                    'state': device['state'],
                    'available_services': self._get_available_services(device['domain'])
                }
                
                # Add specific capabilities
                if 'supports' in device:
                    device_info['capabilities'] = device['supports']
                
                device_list.append(device_info)
            
            return {
                'success': True,
                'devices': device_list,
                'count': len(device_list)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting devices: {str(e)}',
                'devices': []
            }
    
    def _get_available_services(self, domain: str) -> list:
        """Get available services for a domain"""
        service_map = {
            'light': ['turn_on', 'turn_off', 'toggle'],
            'switch': ['turn_on', 'turn_off', 'toggle'],
            'fan': ['turn_on', 'turn_off', 'toggle', 'set_speed'],
            'cover': ['open_cover', 'close_cover', 'stop_cover', 'toggle'],
            'lock': ['lock', 'unlock'],
            'climate': ['set_temperature', 'set_hvac_mode', 'set_fan_mode'],
            'media_player': ['play_media', 'pause', 'play', 'stop', 'volume_set', 'volume_up', 'volume_down'],
            'vacuum': ['start', 'pause', 'stop', 'return_to_base'],
            'water_heater': ['set_temperature', 'turn_on', 'turn_off'],
            'humidifier': ['turn_on', 'turn_off', 'set_humidity']
        }
        
        return service_map.get(domain, ['turn_on', 'turn_off'])
    
    def parse_tool_call(self, tool_string: str) -> Dict[str, Any]:
        """Parse a tool call string like [TOOL:HOME_ASSISTANT service=light.turn_on entity_id=light.living_room brightness=128]"""
        try:
            # Remove the [TOOL:HOME_ASSISTANT and closing ]
            if not tool_string.startswith('[TOOL:HOME_ASSISTANT'):
                return {'success': False, 'message': 'Invalid tool call format'}
            
            params_str = tool_string[20:-1].strip()  # Remove [TOOL:HOME_ASSISTANT and ]
            
            # Parse parameters
            params = {}
            for param in params_str.split():
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
            
            # Execute the tool
            service = params.pop('service', None)
            entity_id = params.pop('entity_id', None)
            
            if not service or not entity_id:
                return {
                    'success': False,
                    'message': 'Both service and entity_id are required'
                }
            
            return self.execute(service, entity_id, **params)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error parsing tool call: {str(e)}'
            }


# Global instance for use by the Manager Model
home_assistant_tool = HomeAssistantTool()

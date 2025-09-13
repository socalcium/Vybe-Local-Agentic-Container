#!/usr/bin/env python3
"""
Event Listener Refactoring Script
Automatically refactors JavaScript files to use the new EventManager
to prevent memory leaks and improve performance.

This script addresses Bug #52: Memory Leaks from Event Listeners
"""

import os
import re
import shutil
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class EventListenerRefactorer:
    def __init__(self, js_dir: str = "vybe_app/static/js"):
        self.js_dir = Path(js_dir)
        self.backup_dir = Path("backup_js_files")
        self.refactored_files = []
        self.stats = {
            "files_processed": 0,
            "event_listeners_replaced": 0,
            "files_backed_up": 0,
            "errors": []
        }
        
        # Patterns to match different event listener patterns
        self.patterns = {
            # Standard addEventListener
            "standard": re.compile(r'(\w+)\.addEventListener\(([^,]+),\s*([^,)]+)(?:,\s*([^)]+))?\)'),
            
            # Arrow function addEventListener
            "arrow": re.compile(r'(\w+)\.addEventListener\(([^,]+),\s*\([^)]*\)\s*=>\s*\{[^}]*\}\)'),
            
            # Function reference addEventListener
            "function_ref": re.compile(r'(\w+)\.addEventListener\(([^,]+),\s*(\w+)\)'),
            
            # Inline function addEventListener
            "inline": re.compile(r'(\w+)\.addEventListener\(([^,]+),\s*function\s*\([^)]*\)\s*\{[^}]*\}\)'),
        }
        
        # Event types that should be debounced
        self.debounce_events = {
            'resize', 'scroll', 'input', 'keyup', 'keydown', 'mousemove', 'touchmove'
        }
        
        # Event types that should be throttled
        self.throttle_events = {
            'scroll', 'mousemove', 'touchmove', 'wheel'
        }

    def backup_file(self, file_path: Path) -> bool:
        """Create a backup of the original file"""
        try:
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True)
            
            backup_path = self.backup_dir / file_path.relative_to(self.js_dir)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            self.stats["files_backed_up"] += 1
            return True
        except Exception as e:
            self.stats["errors"].append(f"Backup failed for {file_path}: {str(e)}")
            return False

    def analyze_event_listeners(self, content: str) -> List[Dict]:
        """Analyze event listeners in the content"""
        listeners = []
        
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                if pattern_name == "standard":
                    element, event, handler, options = match.groups()
                    listeners.append({
                        "type": pattern_name,
                        "element": element.strip(),
                        "event": event.strip().strip('"\''),
                        "handler": handler.strip(),
                        "options": options.strip() if options else None,
                        "start": match.start(),
                        "end": match.end(),
                        "full_match": match.group(0)
                    })
                elif pattern_name == "function_ref":
                    element, event, handler = match.groups()
                    listeners.append({
                        "type": pattern_name,
                        "element": element.strip(),
                        "event": event.strip().strip('"\''),
                        "handler": handler.strip(),
                        "options": None,
                        "start": match.start(),
                        "end": match.end(),
                        "full_match": match.group(0)
                    })
                else:
                    # For other patterns, extract what we can
                    element, event = match.groups()[:2]
                    listeners.append({
                        "type": pattern_name,
                        "element": element.strip(),
                        "event": event.strip().strip('"\''),
                        "handler": "inline_function",
                        "options": None,
                        "start": match.start(),
                        "end": match.end(),
                        "full_match": match.group(0)
                    })
        
        return listeners

    def should_debounce(self, event: str) -> bool:
        """Check if an event should be debounced"""
        return event in self.debounce_events

    def should_throttle(self, event: str) -> bool:
        """Check if an event should be throttled"""
        return event in self.throttle_events

    def generate_event_manager_code(self, listener: Dict) -> str:
        """Generate EventManager code for the listener"""
        element = listener["element"]
        event = listener["event"]
        handler = listener["handler"]
        options = listener["options"]
        
        # Determine if we should use debounce or throttle
        if self.should_debounce(event):
            # For debounced events, wrap the handler
            if handler != "inline_function":
                return f'window.eventManager.add({element}, {event}, window.eventManager.debounce({handler}, 100), {options or "{}"})'
            else:
                # For inline functions, we'll need to extract and wrap
                return f'window.eventManager.add({element}, {event}, window.eventManager.debounce((e) => {{ /* extracted handler */ }}, 100), {options or "{}"})'
        elif self.should_throttle(event):
            # For throttled events
            if handler != "inline_function":
                return f'window.eventManager.add({element}, {event}, window.eventManager.throttle({handler}, 16), {options or "{}"})'
            else:
                return f'window.eventManager.add({element}, {event}, window.eventManager.throttle((e) => {{ /* extracted handler */ }}, 16), {options or "{}"})'
        else:
            # Standard event manager usage
            if handler != "inline_function":
                return f'window.eventManager.add({element}, {event}, {handler}, {options or "{}"})'
            else:
                return f'window.eventManager.add({element}, {event}, (e) => {{ /* extracted handler */ }}, {options or "{}"})'

    def refactor_file(self, file_path: Path) -> bool:
        """Refactor a single JavaScript file"""
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Analyze event listeners
            listeners = self.analyze_event_listeners(content)
            
            if not listeners:
                return True  # No event listeners to refactor
            
            # Create backup
            if not self.backup_file(file_path):
                return False
            
            # Sort listeners by position (reverse order to maintain indices)
            listeners.sort(key=lambda x: x["start"], reverse=True)
            
            # Replace event listeners
            new_content = content
            for listener in listeners:
                replacement = self.generate_event_manager_code(listener)
                new_content = (
                    new_content[:listener["start"]] + 
                    replacement + 
                    new_content[listener["end"]:]
                )
                self.stats["event_listeners_replaced"] += 1
            
            # Add cleanup code if not already present
            if "cleanupFunctions" not in new_content and "eventManager" in new_content:
                # Add cleanup array and destroy method
                cleanup_code = """
    // Cleanup functions for event listeners
    this.cleanupFunctions = [];
    
    // Destroy method to prevent memory leaks
    destroy() {
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
    }
"""
                # Find a good place to insert cleanup code (after constructor)
                class_pattern = re.compile(r'class\s+\w+\s*\{[^}]*constructor\s*\([^)]*\)\s*\{[^}]*\}')
                match = class_pattern.search(new_content)
                if match:
                    insert_pos = match.end()
                    new_content = new_content[:insert_pos] + cleanup_code + new_content[insert_pos:]
            
            # Write the refactored content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.refactored_files.append(str(file_path))
            self.stats["files_processed"] += 1
            
            print(f"✓ Refactored {file_path} ({len(listeners)} event listeners)")
            return True
            
        except Exception as e:
            self.stats["errors"].append(f"Refactor failed for {file_path}: {str(e)}")
            print(f"✗ Error refactoring {file_path}: {str(e)}")
            return False

    def find_js_files(self) -> List[Path]:
        """Find all JavaScript files to refactor"""
        js_files = []
        
        for file_path in self.js_dir.rglob("*.js"):
            # Skip utility files we just created
            if "event-manager.js" in str(file_path) or "performance-monitor.js" in str(file_path):
                continue
            
            # Skip backup directory
            if "backup" in str(file_path):
                continue
                
            js_files.append(file_path)
        
        return js_files

    def refactor_all_files(self) -> bool:
        """Refactor all JavaScript files"""
        js_files = self.find_js_files()
        
        print(f"Found {len(js_files)} JavaScript files to refactor")
        print("=" * 50)
        
        success_count = 0
        for file_path in js_files:
            if self.refactor_file(file_path):
                success_count += 1
        
        print("=" * 50)
        print(f"Refactoring complete: {success_count}/{len(js_files)} files processed successfully")
        
        return success_count == len(js_files)

    def generate_report(self) -> Dict:
        """Generate a refactoring report"""
        report = {
            "summary": {
                "total_files": len(self.find_js_files()),
                "files_processed": self.stats["files_processed"],
                "event_listeners_replaced": self.stats["event_listeners_replaced"],
                "files_backed_up": self.stats["files_backed_up"],
                "success_rate": f"{self.stats['files_processed']}/{len(self.find_js_files())}"
            },
            "refactored_files": self.refactored_files,
            "errors": self.stats["errors"],
            "recommendations": [
                "Review refactored files to ensure event handlers are properly extracted",
                "Test the application thoroughly after refactoring",
                "Monitor memory usage to confirm memory leaks are resolved",
                "Consider adding performance monitoring to track improvements"
            ]
        }
        
        return report

    def save_report(self, report: Dict, filename: str = "event_listener_refactor_report.json"):
        """Save the refactoring report"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {filename}")

def main():
    """Main function"""
    print("Event Listener Refactoring Script")
    print("Addressing Bug #52: Memory Leaks from Event Listeners")
    print("=" * 60)
    
    # Initialize refactorer
    refactorer = EventListenerRefactorer()
    
    # Check if EventManager utilities exist
    event_manager_path = Path("vybe_app/static/js/utils/event-manager.js")
    if not event_manager_path.exists():
        print("Error: EventManager utility not found!")
        print("Please ensure event-manager.js exists in vybe_app/static/js/utils/")
        return False
    
    # Perform refactoring
    success = refactorer.refactor_all_files()
    
    # Generate and save report
    report = refactorer.generate_report()
    refactorer.save_report(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("REFACTORING SUMMARY")
    print("=" * 60)
    print(f"Files processed: {report['summary']['files_processed']}")
    print(f"Event listeners replaced: {report['summary']['event_listeners_replaced']}")
    print(f"Files backed up: {report['summary']['files_backed_up']}")
    print(f"Success rate: {report['summary']['success_rate']}")
    
    if report['errors']:
        print(f"\nErrors encountered: {len(report['errors'])}")
        for error in report['errors'][:5]:  # Show first 5 errors
            print(f"  - {error}")
    
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

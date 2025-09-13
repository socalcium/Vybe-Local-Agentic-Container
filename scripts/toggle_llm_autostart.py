import os
import sys

# Ensure app path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from vybe_app import create_app
from vybe_app.models import db, AppSetting

def set_llm_autostart(enabled: bool):
    app = create_app()
    with app.app_context():
        setting = AppSetting.query.filter_by(key='auto_launch_llm_on_start').first()
        if not setting:
            setting = AppSetting()
            setting.key = 'auto_launch_llm_on_start'
            setting.value = 'true' if enabled else 'false'
            db.session.add(setting)
        else:
            setting.value = 'true' if enabled else 'false'
        db.session.commit()
        print(f"auto_launch_llm_on_start set to {enabled}")

if __name__ == '__main__':
    enable = True
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        enable = arg in ('1', 'true', 'on', 'yes', 'enable')
    set_llm_autostart(enable)



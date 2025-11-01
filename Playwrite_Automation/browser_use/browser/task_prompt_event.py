def build_event_prompt(config):
    return f"""
Automate event creation on the Event Management Platform.

1. Login to {config.event_url} with:
   Username: {config.event_username}
   Password: {config.event_password}

2. Click "Create Event".
3. Fill:
   - Title: GreenEdge Expo – Driving Sustainable Innovation
   - Description: Event on sustainability and green technology.
   - Location: INDIA
   - Start: 2025-11-01T22:00
   - End: 2025-11-01T23:00
4. Submit the event.
5. If "Generate Agenda with AI" is visible, click it.
6. Take a screenshot and save to ./local_screenshots/event_creation_success.png
"""

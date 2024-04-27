# Scheduled Media Player

This project is a Scheduled Media Player designed to manage and automate the playback of media files across a network of devices. The application encompasses a suite of features including media file preview, upload functionality, and the capability to delete media files from a MySQL database. The database models are automatically generated upon application startup, assuming MySQL is accessible.

Key functionalities include creating, editing, and deleting schedules, events, nodes, and node groups, as well as the export and import of node groups. Additionally, the system allows for the monitoring of node connections by sending commands through an API with the device's IP address specified. Users can assign nodes to a group and ping each node to trigger the playback of media content.

It is important to note that this application should be installed on a central machine from which commands will be dispatched. For the playback devices, a separate program named `flask_server` should be installed, which is available in a different repository.

## Features

- Media file preview
- Upload and deletion of media files in the database
- Automatic creation of MySQL database models
- Schedule, event, node, and node group management
- Export and import of node groups
- Monitoring and controlling of node connections via API
- Centralized command dispatching for media content playback

Please note that `flask_server` is required to be installed on each playback device and is maintained separately.

## Getting Started

Follow these instructions to set up the application on your local machine for development and testing purposes.

### Prerequisites

You will need the following tools installed on your system:

- Python 3.x
- MySQL Server
- Any text editor or IDE (like Visual Studio Code)

### Installation

1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Install the required packages using `pip install -r requirements.txt`.
4. Configure your MySQL database settings and other application settings:
   - **Server Name**: Modify `app.config['SERVER_NAME']` to match your server's IP address and port.
   - **SQLAlchemy Database URI**: Change `app.config['SQLALCHEMY_DATABASE_URI']` to your MySQL connection string (e.g., `'mysql+pymysql://username:password@host/database'`).
   - **SQLAlchemy Track Modifications**: If needed, set `app.config['SQLALCHEMY_TRACK_MODIFICATIONS']` to `False`.
   - **Upload Folder**: Update `app.config['UPLOAD_FOLDER']` to the desired folder path for storing uploaded media files.
5. Customize default user accounts:
   - The application initializes with two user accounts: `Super_Admin` and `Admin`. If necessary, modify the usernames and passwords directly in the source code where the `create_users` function is called, prior to starting the server.
6. Run the application using `flask run` or a similar command depending on your setup.

4. Configure your MySQL database settings.
5. Run the application.

Detailed steps for each part will be provided in the subsequent sections.

## Usage

This section provides a step-by-step guide on how to use the application to manage media playback schedules across a network of devices.

### Creating a Schedule
1. **Access the Schedule Creation Interface**: Start by creating a new schedule.
2. **Set Schedule Details**: Provide a name, description, and select a type for the schedule:
   - **Exception**: Highest priority, used for one-time or overriding events.
   - **Special Date**: Used for events that occur on specific dates.
   - **Everyday**: Lowest priority, used for daily recurring events.
3. **Setting Time**: For 'Special Date' schedules, you can also specify the exact time in addition to the date for precise scheduling.

### Managing Media Files
1. **Upload Media**: Navigate to the media management section to upload new media files.
2. **Play Media**: Select any media file from the list and use the play option to test or preview the media.

### Creating an Event
1. **Access the Event Creation Interface**: Combine media files and schedules to create events.
2. **Configure Event Details**: Specify which media file to play and the schedule to follow. Set the start and end times for the event.

### Managing Nodes
1. **Create a Node**: Define a node by its name, location (if necessary), and IP address.
2. **Node Groups**: Create groups for managing multiple nodes. Assign nodes to a group to manage them collectively.

### Node Groups and Events
1. **Assigning Events to Node Groups**: Add events to a node group to ensure that all nodes within the group will play the assigned events.
2. **Unique and Shared Events**: While an event can belong to multiple node groups, a node can only be part of one group at a time.

### Automated Command Dispatch
- The system is designed to automatically dispatch playback commands to nodes.
- **Scheduling Checks**: By default, the application checks the schedule every minute. This interval can be adjusted in the `start_scheduler` function in the code by modifying the line:
  ```python
  scheduler.add_job(lambda: check_and_play_media(app), 'interval', minutes=1)






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
5. Run the application using `flask run` or a similar command depending on your setup.

4. Configure your MySQL database settings.
5. Run the application.

Detailed steps for each part will be provided in the subsequent sections.

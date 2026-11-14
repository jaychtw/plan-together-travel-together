# Plan Together, Travel Together

Two travelers can create or join a project, choose a display name, and contribute text cards to a shared Unscheduled board. The interface supports English and Traditional Chinese. Active tabs poll every two seconds. A returning browser remembers its name for each project.

## Run the shared pilot

Requires Python 3.9 or later. From the repository directory:

```sh
python3 server.py
```

Open http://127.0.0.1:8000. To try two travelers on one computer, open a separate browser profile or private window. Create a project in the first window and use **Enter Existing Project** with the same code in the second. Save a card from each session.

For two devices on a trusted Wi-Fi network, run `HOST=0.0.0.0 python3 server.py` and open the host computer’s LAN address on port 8000 on both devices. Keep the server running. For internet hosting, put this service behind HTTPS with a persistent private data directory. GitHub Pages alone cannot run this Python backend.

The SQLite database in `data/` holds cards, memberships and the code-lookup key. Back up this directory while the server is stopped. Set `TRAVEL_DATA` or `PORT` to override defaults. Treat the project code as an invitation to everyone who has it.

## Milestone scope

This build covers shared access, card creation, saved drafts, attribution and automatic updates. Dated timelines, editing and moving saved cards, images, discussion, archive recovery and PDF export are later milestones.

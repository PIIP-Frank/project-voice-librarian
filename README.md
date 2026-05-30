# Project Voice User Program

## Description

A program for generating, managing, and processing voice samples for Project Voice. 

Contains two separate views:
* Student Librarian: Generate the voice samples for their account. 3 per word + translation.
* Chief Librarian: Manage and process the collected data. 

## Installation
```bash
pip install pyserial
pip install pygame
pip install customtkinter
```

## Usage
```bash
cd src
python main.py
```

Cloud sync is enabled for this app:
* Users are synced from Supabase when the app starts.
* Recorded samples are uploaded to Supabase when saved.
* Admins can pull all cloud samples from the Manage Library screen.

Refer to diagrams for program flow.

## Contributing

Guidelines for contributing to the project. Include how to report issues, submit pull requests, coding standards, etc.

## Contributors

- Frank Cocozza: Programming
- Victor Enyeribe: Flow & UI/UX Design

## Attributions

Credits to third-party libraries, tools, or inspirations used in the project.
PyGame for 2D drawing.
CustomTkinter

## License

See License (MIT License)

## Contact

frank@piipfoundation.org
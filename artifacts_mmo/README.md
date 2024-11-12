# Artifacts MMO API Wrapper

This is a Python wrapper for the Artifacts MMO API. It provides a convenient way to interact with the game's API, allowing you to automate tasks, retrieve game data, and build custom applications.

## Features

* **Object-oriented structure:** The wrapper is organized into classes, making it easy to use and understand.
* **Comprehensive API coverage:**  Includes methods for accessing character data, inventory, bank, grand exchange, tasks, crafting, and more.
* **Error handling:** Provides informative error messages for API exceptions.
* **Automatic cooldown handling:**  The wrapper automatically waits for cooldown periods before making subsequent requests.
* **Threading support:** Allows concurrent API calls for faster processing.

## Installation

To install the wrapper, you can simply copy the `__init__.py` file into your project directory.

## Usage

Here's a basic example of how to use the wrapper:

```python
from artifacts_mmo import ArtifactsAPI

# Replace with your actual API token and character name
api = ArtifactsAPI(api_token="your_api_token", character_name="your_character_name")

# Get character data
character = api.char
print(character)  # Output character stats

# Move the character
api.actions.move(x=-1, y=0)

# Gather resources (e.g., mine, woodcut, fish)
api.actions.gather()
```

Examples
Please view [https://github.com/Veillax/ArtifactsMMO-S3-Wrapper/tree/main/examples](https://github.com/Veillax/ArtifactsMMO-S3-Wrapper/tree/main/examples)

Documentation
You can find detailed documentation for the Artifacts MMO API here: https://docs.artifactsmmo.com/

Contributing
Contributions are welcome! If you find any bugs or have suggestions for improvements, please feel free to open an issue or submit a pull request.

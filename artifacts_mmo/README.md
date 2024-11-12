# Artifacts MMO API Wrapper

## Overview
This is a Python wrapper for interacting with the Artifacts MMO API, providing an easy way to interact with the game's data, perform in-game actions, and manage character and account information. This library simplifies API requests and provides a range of features to integrate with Artifacts MMO's online functionalities.

### Features
- **Character Management**: Create, delete, and manage character data.
- **In-Game Actions**: Move, gather, craft, fight, and other interactive commands.
- **Task Management**: Accept, complete, and exchange tasks from the taskmaster.
- **Grand Exchange**: Manage buy and sell orders, view order history.
- **Inventory and Equipment Management**: View, equip, and manage items.
- **Bank and Gold Management**: Deposit and withdraw gold or items.
- **Leaderboard and Events**: View event and leaderboard data.

## Installation

Please use PyPi to install this wrapper

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

Contributing
Contributions are welcome! If you find any bugs or have suggestions for improvements, please feel free to open an issue or submit a pull request.

## Disclaimer

This wrapper is a third-party tool and is not officially affiliated with Artifacts MMO. Use it responsibly and at your own risk. Be aware of the game's terms of service and avoid any actions that could violate them.

### Disclaimer
Some of the following text is taken from the ArtifactsMMO Website to ensure it is accurate and well put for new developers to be able to understand. It is adapted to suit this package. 

## How to begin playing ArtifactsMMO
Artifacts is an asynchronous MMORPG in which you can control up to 5 characters at the same time. Your characters can fight monsters, gather resources, craft items and much more.

Unlike a traditional game, you'll have to write your own scripts in your preferred programming language to control your characters via an API.

This wrapper is an easy way to get started with playing ArtifactsMMO Season 3. It allows you to access the API without writing too much complex code.

For another quick start, you can write your first Javascript scripts directly in the client's code editor, otherwise you can use any language you like on your own IDE. You can see examples in other programming languages in the [Reference API](https://api.artifactsmmo.com/docs/#/).

## Before You Begin
The first step is to [create your account](https://artifactsmmo.com/account/create) and your first character [by logging in](https://artifactsmmo.com/account/characters). After that you'll need your token, which you can find [on your account](https://artifactsmmo.com/account/).

![API Token Box](https://artifactsmmo.com/images/docs/token.png)

**⚠️ The token is used by the server to identify you when you make requests. It is important to keep it secret.**

You can now open the game client by [clicking here](https://artifactsmmo.com/client).

**Ready to start?**

Client
The client lets you play with your characters and see all the information you need. It's literally your dashboard for following your characters in real time.

![Client](https://artifactsmmo.com/images/docs/scgame1.png)

On the top left, you have your logs, i.e. all the actions performed by your characters, and when you click on a log, you get all the details.

![Log](https://artifactsmmo.com/images/docs/log_example.png)

At bottom left, a list of your characters, and when you click on a character, you can control it and see all the information about it.

And finally, in the top right-hand corner, you'll find the “Code Editor” button, which opens the Javascript code editor.

Firefox does not fully support the editor. Please use a chromimum-based web browser such as Chrome, Brave or Edge.

The IDE runs in a Node.js environment, so you need to type node name_of_your_script.js in the terminal to run it. By default, the script is called index.js, so you can type node index.js

![IDE](https://artifactsmmo.com/images/docs/ide.png)

### ⚠️ For this wrapper, we won't be able to use the code editor, as this is a Python wrapper, not a Node.js wrapper. Please use an IDE on your computer for the most security, such as [Visual Studio Code](https://code.visualstudio.com/) or [PyCharm Community](https://www.jetbrains.com/pycharm/)


### Moving
The 2D world uses a movement system with X,Y coordinates.

![Map](https://artifactsmmo.com/images/docs/map.png)

To move, you'll need to know the coordinates of the map you want to move your character to. There are several ways of doing this, including using an API request, but for the purposes of this guide, we're going to use the information available in the client.

If you look at (0,1) on the map, you'll find the chicken. A low-level monster that's easy enough to kill when you start the game. We're going to fight him.

![Chicken](https://artifactsmmo.com/images/docs/chicken.png)


### For more explanation on how the game works, please visit [https://docs.artifactsmmo.com/quickstart/introduction](https://docs.artifactsmmo.com/quickstart/introduction). 
### For the documentation on this wrapper, please visit [Website is not available right now, please check back later](https://docs.veillax.com/artifacts_mmo_wrapper)

## Links
[ArtifactsMMO Website](https://artifactsmmo.com/)  
[ArtifactsMMO Discord](https://discord.com/invite/prEBQ8a6Vs)  
[ArtifactsMMO Docs](https://docs.artifactsmmo.com/)  
[ArtifactsMMO Encyclopidea](https://artifactsmmo.com/encyclopedia)  
[ArtifactsMMO API Docs](https://api.artifactsmmo.com/docs/#/)


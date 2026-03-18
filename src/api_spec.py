API_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Connect Four API",
        "version": "1.0.0",
        "description": (
            "REST API for playing Connect Four. Supports creating games, "
            "making moves, and long-polling for turn notifications."
        ),
    },
    "paths": {
        "/games": {
            "post": {
                "summary": "Create a new game",
                "operationId": "createGame",
                "responses": {
                    "201": {
                        "description": "Game created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    }
                },
            },
            "get": {
                "summary": "List all games",
                "operationId": "listGames",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "enum": [
                                "in_progress",
                                "player_1_wins",
                                "player_2_wins",
                                "draw",
                            ],
                        },
                        "description": "Filter games by status",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "List of games",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/GameSummary"
                                    },
                                }
                            }
                        },
                    }
                },
            },
        },
        "/games/{game_id}": {
            "get": {
                "summary": "Get game state",
                "operationId": "getGame",
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Game state",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/games/{game_id}/turn": {
            "get": {
                "summary": "Long-poll for turn",
                "operationId": "waitForTurn",
                "description": (
                    "Blocks until it is the specified player's turn or the "
                    "game ends. Times out after 30 seconds."
                ),
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "player",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "integer", "enum": [1, 2]},
                        "description": "Player number (1 or 2)",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "It is now this player's turn or the game ended",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid or missing player parameter",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "408": {
                        "description": "Long-poll timeout",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/games/{game_id}/moves": {
            "post": {
                "summary": "Make a move",
                "operationId": "makeMove",
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MoveRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Move accepted",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid move",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "GameState": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Unique game identifier",
                    },
                    "board": {
                        "type": "array",
                        "description": "6x7 board grid (0=empty, 1=player 1, 2=player 2)",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1, 2]},
                        },
                    },
                    "current_player": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "Player whose turn it is",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "player_1_wins",
                            "player_2_wins",
                            "draw",
                        ],
                    },
                },
            },
            "GameSummary": {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "player_1_wins",
                            "player_2_wins",
                            "draw",
                        ],
                    },
                    "current_player": {"type": "integer", "enum": [1, 2]},
                },
            },
            "MoveRequest": {
                "type": "object",
                "required": ["column", "player"],
                "properties": {
                    "column": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 6,
                        "description": "Column to drop piece into (0-6)",
                    },
                    "player": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "Player making the move",
                    },
                },
            },
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message",
                    }
                },
            },
        }
    },
}

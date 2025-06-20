#!/usr/bin/env python3
"""
MCP Server for listing files in H:\dancers_content
Communicates via stdin/stdout with Claude Desktop
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

class DancersContentServer:
    def __init__(self):
        self.base_path = Path(r"H:\dancers_content")
        if not self.base_path.exists():
            raise FileNotFoundError(f"Directory not found: {self.base_path}")

    def list_files(self, recursive: bool = False, file_pattern: str = "*", 
                   include_metadata: bool = False, max_files: int = 1000) -> List[Dict]:
        """List files with optional filtering and metadata"""
        files = []
        
        try:
            if recursive:
                pattern_path = self.base_path.rglob(file_pattern)
            else:
                pattern_path = self.base_path.glob(file_pattern)
            
            for i, file_path in enumerate(pattern_path):
                if i >= max_files:  # Safety limit
                    break
                    
                if file_path.is_file():
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(self.base_path)),
                        "full_path": str(file_path)
                    }
                    
                    if include_metadata:
                        stat = file_path.stat()
                        file_info.update({
                            "size": stat.st_size,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "extension": file_path.suffix.lower()
                        })
                    
                    files.append(file_info)
            
            return sorted(files, key=lambda x: x["name"].lower())
            
        except Exception as e:
            raise Exception(f"Error listing files: {str(e)}")

    async def handle_call_tool(self, name: str, arguments: Dict) -> Dict:
        """Handle tool calls"""
        if name == "list_dancers_files":
            try:
                recursive = arguments.get("recursive", False)
                file_pattern = arguments.get("file_pattern", "*")
                include_metadata = arguments.get("include_metadata", False)
                max_files = arguments.get("max_files", 1000)
                
                files = self.list_files(recursive, file_pattern, include_metadata, max_files)
                
                summary = f"Found {len(files)} files in {self.base_path}"
                if recursive:
                    summary += " (recursive)"
                if file_pattern != "*":
                    summary += f" matching '{file_pattern}'"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"{summary}\n\n" + json.dumps(files, indent=2)
                        }
                    ]
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text", 
                            "text": f"Error: {str(e)}"
                        }
                    ],
                    "isError": True
                }
        else:
            raise ValueError(f"Unknown tool: {name}")

    async def run(self):
        """Main server loop - handles stdin/stdout communication"""
        async def read_request():
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, sys.stdin.readline)
            return json.loads(line.strip()) if line.strip() else None

        async def write_response(response):
            print(json.dumps(response, separators=(',', ':')))
            sys.stdout.flush()

        while True:
            try:
                request = await read_request()
                if not request:
                    break

                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")

                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {
                                "name": "dancers-content-server",
                                "version": "1.0.0"
                            }
                        }
                    }

                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "list_dancers_files",
                                    "description": f"List files in {self.base_path}",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "recursive": {
                                                "type": "boolean",
                                                "description": "Search subdirectories",
                                                "default": False
                                            },
                                            "file_pattern": {
                                                "type": "string", 
                                                "description": "File pattern (*.jpg, *.mp4, etc.)",
                                                "default": "*"
                                            },
                                            "include_metadata": {
                                                "type": "boolean",
                                                "description": "Include file size and dates", 
                                                "default": False
                                            },
                                            "max_files": {
                                                "type": "integer",
                                                "description": "Maximum files to return",
                                                "default": 1000
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }

                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    result = await self.handle_call_tool(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }

                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }

                await write_response(response)

            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0", 
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                await write_response(error_response)

if __name__ == "__main__":
    server = DancersContentServer()
    asyncio.run(server.run())
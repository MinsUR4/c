#!/usr/bin/env python3
"""
Remote Desktop Monitor - Server Script
Run this on your main PC to share the screen
"""

import socket
import threading
import time
import io
import struct
from PIL import ImageGrab
import zlib

class DesktopServer:
    def __init__(self, host='0.0.0.0', port=5900):
        self.host = host
        self.port = port
        self.running = False
        self.clients = []
        self.server_socket = None
        
    def start_server(self):
        """Start the desktop sharing server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"🖥️  Desktop Monitor Server started on {self.host}:{self.port}")
            print("📱 Waiting for laptop connections...")
            print("🔴 Press Ctrl+C to stop the server")
            
            # Start screen capture thread
            capture_thread = threading.Thread(target=self.capture_and_send)
            capture_thread.daemon = True
            capture_thread.start()
            
            # Accept client connections
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"📱 Laptop connected from {addr}")
                    self.clients.append(client_socket)
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("❌ Socket error occurred")
                    
        except Exception as e:
            print(f"❌ Error starting server: {e}")
        finally:
            self.stop_server()
    
    def handle_client(self, client_socket, addr):
        """Handle individual client connection"""
        try:
            while self.running:
                # Keep connection alive
                time.sleep(1)
        except Exception as e:
            print(f"❌ Client {addr} disconnected: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
    
    def capture_and_send(self):
        """Capture screen and send to all connected clients"""
        while self.running:
            try:
                # Capture screen
                screenshot = ImageGrab.grab()
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='JPEG', quality=60)
                img_data = img_buffer.getvalue()
                
                # Compress data
                compressed_data = zlib.compress(img_data)
                
                # Send to all connected clients
                for client_socket in self.clients[:]:  # Copy list to avoid modification during iteration
                    try:
                        # Send data length first, then data
                        data_length = struct.pack('!I', len(compressed_data))
                        client_socket.send(data_length)
                        client_socket.send(compressed_data)
                    except Exception as e:
                        print(f"❌ Error sending to client: {e}")
                        if client_socket in self.clients:
                            self.clients.remove(client_socket)
                        client_socket.close()
                
                # Control frame rate (adjust as needed)
                time.sleep(0.1)  # ~10 FPS
                
            except Exception as e:
                print(f"❌ Error capturing screen: {e}")
                time.sleep(1)
    
    def stop_server(self):
        """Stop the server and close all connections"""
        self.running = False
        print("\n🔴 Stopping server...")
        
        # Close all client connections
        for client_socket in self.clients:
            client_socket.close()
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        print("✅ Server stopped successfully")

def main():
    server = DesktopServer()
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.stop_server()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        server.stop_server()

if __name__ == "__main__":
    main()

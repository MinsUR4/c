#!/usr/bin/env python3
"""
Remote Desktop Monitor - Client Script
Run this on your laptop to view the main PC's screen
"""

import socket
import struct
import threading
import time
import io
import zlib
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

class DesktopViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🖥️ Remote Desktop Viewer")
        self.root.geometry("1200x700")
        self.root.configure(bg='#2d2d2d')
        
        self.socket = None
        self.connected = False
        self.running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Control frame
        control_frame = tk.Frame(self.root, bg='#2d2d2d', pady=10)
        control_frame.pack(fill='x')
        
        # Connection controls
        tk.Label(control_frame, text="PC IP Address:", 
                bg='#2d2d2d', fg='white', font=('Arial', 10)).pack(side='left', padx=5)
        
        self.ip_entry = tk.Entry(control_frame, width=15, font=('Arial', 10))
        self.ip_entry.pack(side='left', padx=5)
        self.ip_entry.insert(0, "192.168.1.100")  # Default IP - change as needed
        
        tk.Label(control_frame, text="Port:", 
                bg='#2d2d2d', fg='white', font=('Arial', 10)).pack(side='left', padx=(20,5))
        
        self.port_entry = tk.Entry(control_frame, width=8, font=('Arial', 10))
        self.port_entry.pack(side='left', padx=5)
        self.port_entry.insert(0, "5900")
        
        # Connect button
        self.connect_button = tk.Button(
            control_frame, text="🔗 Connect", 
            command=self.toggle_connection,
            bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
            padx=20, pady=5
        )
        self.connect_button.pack(side='left', padx=20)
        
        # Status label
        self.status_label = tk.Label(
            control_frame, text="📴 Disconnected", 
            bg='#2d2d2d', fg='#ff6b6b', font=('Arial', 10, 'bold')
        )
        self.status_label.pack(side='left', padx=20)
        
        # Exit button
        exit_button = tk.Button(
            control_frame, text="❌ Exit", 
            command=self.exit_application,
            bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
            padx=20, pady=5
        )
        exit_button.pack(side='right', padx=10)
        
        # Separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', pady=5)
        
        # Screen display frame
        self.screen_frame = tk.Frame(self.root, bg='#1a1a1a', relief='sunken', bd=2)
        self.screen_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Screen label
        self.screen_label = tk.Label(
            self.screen_frame, 
            text="🖥️ Remote screen will appear here\n\nEnter your PC's IP address and click Connect",
            bg='#1a1a1a', fg='#888', font=('Arial', 14),
            justify='center'
        )
        self.screen_label.pack(expand=True)
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)
        
        # Key bindings
        self.root.bind('<Escape>', lambda e: self.disconnect())
        self.root.bind('<F11>', self.toggle_fullscreen)
        
        # Add keyboard shortcuts info
        shortcuts_label = tk.Label(
            self.root, 
            text="💡 Shortcuts: ESC to disconnect | F11 for fullscreen | Ctrl+C in terminal to stop server",
            bg='#2d2d2d', fg='#888', font=('Arial', 8)
        )
        shortcuts_label.pack(side='bottom', pady=5)
        
    def toggle_connection(self):
        """Toggle connection to the desktop server"""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to the desktop server"""
        try:
            host = self.ip_entry.get().strip()
            port = int(self.port_entry.get().strip())
            
            if not host:
                messagebox.showerror("Error", "Please enter the PC's IP address")
                return
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 second timeout
            self.socket.connect((host, port))
            
            self.connected = True
            self.running = True
            
            # Update UI
            self.connect_button.config(text="🔌 Disconnect", bg='#ff6b6b')
            self.status_label.config(text="🟢 Connected", fg='#4CAF50')
            self.ip_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self.receive_screen)
            receive_thread.daemon = True
            receive_thread.start()
            
            print(f"✅ Connected to {host}:{port}")
            
        except socket.timeout:
            messagebox.showerror("Connection Error", 
                               "Connection timed out. Make sure:\n"
                               "1. The server is running on your PC\n"
                               "2. The IP address is correct\n"
                               "3. Firewall allows connections on port 5900")
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", 
                               "Connection refused. Make sure the server is running on your PC.")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
    
    def disconnect(self):
        """Disconnect from the desktop server"""
        self.running = False
        self.connected = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        # Update UI
        self.connect_button.config(text="🔗 Connect", bg='#4CAF50')
        self.status_label.config(text="📴 Disconnected", fg='#ff6b6b')
        self.ip_entry.config(state='normal')
        self.port_entry.config(state='normal')
        
        # Reset screen display
        self.screen_label.config(
            text="🖥️ Remote screen will appear here\n\nEnter your PC's IP address and click Connect"
        )
        
        print("✅ Disconnected from server")
    
    def receive_screen(self):
        """Receive and display screen updates"""
        while self.running and self.connected:
            try:
                # Receive data length
                length_data = self.receive_exact(4)
                if not length_data:
                    break
                
                data_length = struct.unpack('!I', length_data)[0]
                
                # Receive compressed image data
                compressed_data = self.receive_exact(data_length)
                if not compressed_data:
                    break
                
                # Decompress and display
                img_data = zlib.decompress(compressed_data)
                img = Image.open(io.BytesIO(img_data))
                
                # Resize image to fit the display area
                self.display_image(img)
                
            except Exception as e:
                if self.running:
                    print(f"❌ Error receiving screen: {e}")
                break
        
        # Clean up on error or disconnection
        if self.connected:
            self.root.after(0, self.disconnect)
    
    def receive_exact(self, num_bytes):
        """Receive exactly num_bytes from socket"""
        data = b''
        while len(data) < num_bytes and self.running:
            chunk = self.socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def display_image(self, img):
        """Display the received image"""
        try:
            # Get display area size
            self.screen_frame.update_idletasks()
            frame_width = self.screen_frame.winfo_width()
            frame_height = self.screen_frame.winfo_height()
            
            if frame_width <= 1 or frame_height <= 1:
                return
            
            # Calculate scaling to fit the frame while maintaining aspect ratio
            img_width, img_height = img.size
            scale_x = frame_width / img_width
            scale_y = frame_height / img_height
            scale = min(scale_x, scale_y) * 0.95  # Leave some margin
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(resized_img)
            
            # Update display
            self.screen_label.config(image=photo, text="")
            self.screen_label.image = photo  # Keep a reference
            
        except Exception as e:
            print(f"❌ Error displaying image: {e}")
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)
        
        if not is_fullscreen:
            # Hide cursor in fullscreen
            self.root.config(cursor="none")
        else:
            # Show cursor when exiting fullscreen
            self.root.config(cursor="")
    
    def exit_application(self):
        """Exit the application"""
        if self.connected:
            self.disconnect()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the viewer application"""
        print("🖥️  Remote Desktop Viewer")
        print("📱 Enter your PC's IP address and click Connect")
        print("💡 Press ESC to disconnect, F11 for fullscreen")
        self.root.mainloop()

def main():
    try:
        viewer = DesktopViewer()
        viewer.run()
    except KeyboardInterrupt:
        print("\n🛑 Application closed by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()

import cherrypy
import socket
import json

# Configuration
SOCKET_FILE = "/tmp/twitch_matrix.sock"
PORT = 8080

def send_command(command_dict):
    """Sends a command to the daemon via a UNIX socket."""
    try:
        # Create a UDS socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_FILE)
        sock.sendall(json.dumps(command_dict).encode('utf-8'))
    except Exception as e:
        print(f"Failed to send command: {e}")
        # Re-raise as a CherryPy HTTP error to give feedback to the user
        raise cherrypy.HTTPError(500, f"Daemon not responding: {e}")
    finally:
        sock.close() #type: ignore
    return f"Command '{command_dict.get('command')}' sent successfully."

class WebServer:
    @cherrypy.expose
    def start(self):
        return send_command({'command': 'start'})

    @cherrypy.expose
    def stop(self):
        return send_command({'command': 'stop'})

    @cherrypy.expose
    def fireworks(self):
        return send_command({'command': 'fireworks'})

    @cherrypy.expose
    def heart(self):
        return send_command({'command': 'heart'})

    @cherrypy.expose
    def smiley(self):
        return send_command({'command': 'smiley'})

if __name__ == '__main__':
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': PORT
    })
    
    print(f"Control panel starting on http://0.0.0.0:{PORT}")
    print("Endpoints available: /start, /stop, /fireworks, /heart, /smiley")
    
    cherrypy.quickstart(WebServer(), '/')

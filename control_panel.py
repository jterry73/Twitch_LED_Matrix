import cherrypy
import socket
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import os

# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
logFile = '/app/logs/control_panel.log'
my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)
app_log.addHandler(logging.StreamHandler(sys.stdout))

# Configuration
SOCKET_FILE = "/tmp/twitch_matrix.sock"
PORT = 8080
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def send_command(command_dict):
    """Sends a command to the daemon via a UNIX socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_FILE)
        sock.sendall(json.dumps(command_dict).encode('utf-8'))
    except Exception as e:
        app_log.error(f"Failed to send command: {e}")
        raise cherrypy.HTTPError(500, f"Daemon not responding: {e}")
    finally:
        sock.close()
    
    response = f"Command '{command_dict.get('command')}' sent successfully."
    app_log.info(response)
    return response

class WebServer:
    @cherrypy.expose
    def index(self):
        """Serves the main index.html file."""
        return open(os.path.join(CURRENT_DIR, 'index.html'))

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def update_config(self):
        """Receives new configuration and sends it to the daemon."""
        config_data = cherrypy.request.json
        return send_command({'command': 'update_config', 'data': config_data})

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
    config = {
        '/': {
            'tools.staticdir.root': CURRENT_DIR,
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static'
        }
    }
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': PORT
    })
    
    app_log.info(f"Control panel starting on http://0.0.0.0:{PORT}")
    
    cherrypy.quickstart(WebServer(), '/', config=config)

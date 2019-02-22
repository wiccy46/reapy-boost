import reapy
from reapy.errors import OutsideREAPERError
from reapy.reascripts import activate_reapy_server

from configparser import ConfigParser
import json
import os

REAPY_SERVER_PORT = 2306
WEB_INTERFACE_PORT = 2307


class Config(ConfigParser):

    """Parser for REAPER .ini file."""

    def __init__(self):
        super(Config, self).__init__()
        self.read(reapy.get_ini_file())

    def write(self):
        with open(reapy.get_ini_file(), "w") as f:
            super(Config, self).write(f, False)


def create_new_web_interface(port):
    """
    Create a Web interface in REAPER at a specified port.

    It is added by writing a line directly in REAPER .ini file. Thus
    it will only be available on restart.

    Parameters
    ----------
    port : int
        Web interface port.
    """
    config = Config()
    csurf_count = int(config["reaper"]["csurf_cnt"])
    csurf_count += 1
    config["reaper"]["csurf_cnt"] = str(csurf_count)
    key = "csurf_{}".format(csurf_count - 1)
    config["reaper"][key] = "HTTP 0 {} '' 'index.html' 0 ''".format(port)
    config.write()


def delete_web_interface(port):
    """
    Delete Web interface listening to a specified port.

    It is deleted by writing a line directly in REAPER .ini file. Thus
    it will only be deleted on restart.

    Parameters
    ----------
    port : int
        Web interface port.
    """
    config = Config()
    csurf_count = int(config["reaper"]["csurf_cnt"])
    csurf_count -= 1
    config["reaper"]["csurf_cnt"] = str(csurf_count)
    key = "csurf_{}".format(csurf_count)
    del config["reaper"][key]
    config.write()


def disable_dist_api():
    """
    Disable distant API.

    Delete ``reapy`` Web interface, and remove the ReaScript
    ``reapy.reascripts.activate_reapy_server`` from the
    Actions list.
    """
    if not reapy.is_inside_reaper():
        raise OutsideREAPERError
    delete_web_interface(WEB_INTERFACE_PORT)
    reascript_path = get_activate_reapy_server_path()
    reapy.remove_reascript(reascript_path)
    message = (
        "reapy will be disabled as soon as you restart REAPER."
    )
    reapy.show_message_box(message)


def enable_dist_api():
    """
    Enable distant API.

    Create a Web interface and add the ReaScript
    ``reapy.reascripts.activate_reapy_server`` to the Actions list.
    """
    if not reapy.is_inside_reaper():
        raise OutsideREAPERError
    create_new_web_interface(WEB_INTERFACE_PORT)
    reascript_path = get_activate_reapy_server_path()
    action_id = reapy.add_reascript(reascript_path)
    command_name = json.dumps(reapy.get_command_name(action_id))
    section, key, value = "reapy", "activate_reapy_server", command_name
    reapy.set_ext_state(section, key, value, persist=True)
    message = (
        "reapy successfully enabled!\n\nPlease restart REAPER.\n\nYou will "
        "then be able to import reapy from the outside."
    )
    reapy.show_message_box(message)


def get_activate_reapy_server_path():
    """Return path to the ``activate_reapy_server`` ReaScript."""
    return os.path.abspath(activate_reapy_server.__file__)
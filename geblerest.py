import json
import re

import os
import traceback

from flask import Flask, jsonify, render_template, request
from flask import redirect
from flask import url_for

import mipow


config = {}
lights = {}

app = Flask(__name__)


mac_pattern = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
def is_valid_mac(mac):
    return mac_pattern.match(mac)

name_pattern = re.compile('\w')
def is_valid_light_name(name):
    return name_pattern.match(name)

def load_config(settingsfile):
    try:
        if os.path.isfile(settingsfile):
            f = open(settingsfile,'r')
            config = json.load(f)
        else:
            config = {}
        return config
    except Exception as e:
        raise e

def save_config(settingsfile, config):
        f = open(settingsfile, 'w')
        f.write(json.dumps(config))
        f.close()

def lamp_get_initial(name):
    if not name in config:
        raise Exception("Light not in known config")
    current_light = config[name]
    if name not in lights:
        print("New light")
        new_mipow = mipow.mipow(current_light["mac"])
        new_mipow.connect()
        lights[name] = new_mipow
    else:
        print("Old light")
        new_mipow = lights[name]
    return new_mipow

def lamp_get_state(name):
    new_mipow = lamp_get_initial(name)
    state = {"name":name}
    state["power_on"] = new_mipow.get_on()
    colors = new_mipow.get_colour()
    state["red"] = colors[0] if type(colors[0]) is int else int(colors[0].encode('hex'), 16)
    state["green"] = colors[1] if type(colors[1]) is int else int(colors[1].encode('hex'), 16)
    state["blue"] = colors[2] if type(colors[2]) is int else int(colors[2].encode('hex'), 16)
    whites = new_mipow.get_white()
    state["white"] = whites if type(whites) is int else int(whites.encode('hex'), 16)
    return state

def lamp_set_power(name, power_on=None):
    new_mipow = lamp_get_initial(name)
    if power_on == None:
        power_on = not new_mipow.get_on()
    if power_on:
        new_mipow.on()
    else:
        new_mipow.off()

def lamp_set_color(name, red, green, blue,white):
    new_mipow = lamp_get_initial(name)
    new_mipow.set_rgbw(red, green, blue, white)

## Convenience method for turning a bulb on!
@app.route('/lights/<name>/power/<power>')
@app.route('/lights/<name>/power/')
def flask_set_power(name, power = None):
    try:
        if power is not None:
            if(power in ["on", "off"]):
                power = True if power == "on" else False
            else:
                power = bool(power)
        lamp_set_power(name, power)
        return jsonify({"result": "ok", "light": lamp_get_state(name)})
    except Exception as e:
        return jsonify({"result": "error", "error": str(e)})


@app.route('/lights/<name>/<mac>', methods=['POST'])
@app.route('/lights/<mac>', methods=['POST'])
def flask_add_new(mac,name=False):
    try:
        if not is_valid_mac(mac):
            raise Exception("Invalid MAC address")
        if not name:
            name = "light_" + str(len(config) + 1)
        if not is_valid_light_name(name):
            raise Exception("Light name was invalid")
        config[name] = ({"mac":mac, "name":name})
        save_config(settingsfile, config)
        return redirect(url_for('flask_show_lights'))
    except Exception as e:
        return jsonify({"result":"error","error":str(e) })

@app.route('/lights/<name>', methods=['PUT'])
def flask_change_current(name):
    try:
        if name in config:
            content = request.get_json()
            lamp_set_power(name, content["power_on"])
            lamp_set_color(name, content["red"], content["green"], content["blue"], content["white"])
            return redirect(url_for('flask_get', name=name), code=303)
        else:
             raise Exception("Light was not in the list of configured lights")
    except Exception as e:
        return jsonify({"result":"error","error":str(e)})


@app.route('/lights/<name>', methods=['DELETE'])
def flask_delete(name):
    try:
        if name in config:
            del config[name]
            save_config(settingsfile, config)
            return redirect(url_for('lights/' + name))
        else:
            raise Exception("Light was not in the list of configured lights")
    except Exception as e:
        return jsonify({"result":"error","error":str(e)})

@app.route('/lights/<name>')
def flask_get(name):
    try:
        return jsonify({name:lamp_get_state(name)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"result":"error","error":str(e)})

@app.route('/lights/', methods=["GET", "PUT", "POST", "DELETE"])
def flask_show_lights():
    return jsonify({"lights":config})

@app.route('/')
def flask_show_test():
    return render_template('resttesttest/index.html')

settingsfile = "./config.json"
config = load_config(settingsfile)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=1000, debug=True)

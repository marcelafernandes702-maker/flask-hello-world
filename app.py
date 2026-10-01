from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api')
def index():
    return jsonify({
        "servidor": "Stumble Rewald",
        "versao": "0.65",
        "discord": "https://discord.gg/sgrewald",
        "status": "online"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)


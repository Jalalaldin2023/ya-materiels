#!/bin/bash
echo "🔧 Démarrage de Quincaillerie Pro..."
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
cd "$(dirname "$0")/backend"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!
sleep 2
echo ""
echo "✅ Application démarrée !"
echo "👉 Ouvrez votre navigateur : http://localhost:8000"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter."
wait $SERVER_PID

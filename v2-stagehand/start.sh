#!/bin/bash

# Start backend
cd /app/backend
python main.py &
BACKEND_PID=$!

# Start frontend
cd /app/frontend
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!

# Wait for both
wait $BACKEND_PID $FRONTEND_PID

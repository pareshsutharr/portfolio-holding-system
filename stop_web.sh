#!/bin/zsh

stopped=0

for port in 3001 8000; do
  pids=($(lsof -ti tcp:$port 2>/dev/null))
  if (( ${#pids[@]} > 0 )); then
    kill "${pids[@]}" 2>/dev/null
    echo "Stopped Portfolio Analyzer process on port $port."
    stopped=1
  fi
done

if (( stopped == 0 )); then
  echo "Portfolio Analyzer is not currently running."
fi

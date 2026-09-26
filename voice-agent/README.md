# Brightside Dental voice agent

A working voice receptionist you can talk to in your browser. Claude handles the
conversation and calls booking tools; Chrome's built-in speech recognition and
text-to-speech handle the audio.

## Run it in VS Code

You need Python 3.10 or newer, Chrome or Edge, and an Anthropic API key from
https://console.anthropic.com.

1. **Open the folder.** In VS Code choose File > Open Folder and pick `voice-agent`.
   Install the Python extension if VS Code suggests it.

2. **Create a virtual environment.** Open the terminal (View > Terminal) and run:

   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   Windows (PowerShell):
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If VS Code asks whether to use the new environment for this workspace, click Yes.

3. **Install dependencies.**
   ```
   pip install -r requirements.txt
   ```

4. **Add your API key.** Copy `.env.example` to a new file named `.env` and replace
   the placeholder with your key.

5. **Start the server.** Either run `python app.py` in the terminal, or press F5
   and choose "Run voice agent" (this lets you set breakpoints).

6. **Open http://localhost:5050 in Chrome or Edge**, click Start call, and allow
   microphone access.

The VS Code terminal prints the whole conversation, including every tool call
and its result, so you can see exactly what the agent is doing.

## Things to try

- "I'd like to book a cleaning for next Tuesday."
- "I need to reschedule. My name is Jane Doe, born April 12th, 1990."
  (A demo appointment exists for Jane Doe.)
- "Do you take Cigna?"
- "I have really bad swelling in my jaw."
- "Can I talk to a real person?"

## Files

- `prompt.py`: Maya's persona, rules, and clinic info. Edit this first.
- `tools.py`: the booking tools and an in-memory calendar. Replace the function
  bodies with calls to your real scheduling system.
- `app.py`: the server and the loop that runs Claude and its tools.
- `static/index.html`: the call screen, microphone, and speech output.

## Troubleshooting

- **"Missing ANTHROPIC_API_KEY"**: the `.env` file is missing or misnamed. It must
  be called exactly `.env` and sit next to `app.py`.
- **Microphone does nothing**: use Chrome or Edge (Firefox and some Safari
  versions lack speech recognition), open the page at `localhost`, and check the
  microphone permission in the address bar. You can always type instead.
- **Port already in use**: set `PORT=5051` in `.env`.
- **Responses feel slow**: keep the default Haiku model. Larger models are smarter
  but add noticeable delay on a voice call.

## Notes

- Chrome's speech recognition sends audio to Google's servers to transcribe it.
- Appointments live in memory and reset when you restart the server.
- For real phone calls and more natural voices, move to a pipeline framework such
  as Pipecat or LiveKit Agents, or a hosted platform like Vapi or Retell, and reuse
  `prompt.py` and `tools.py`.

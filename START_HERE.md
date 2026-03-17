# Start Here

## The simplest way to open Snowmass next time
1. Open this folder: `C:\Users\14077\Documents\GitHub\Snowmass`
2. Double-click `start-local.bat`
3. Wait a few seconds
4. Your browser should open the app automatically
5. If it does not open by itself, click this address in your browser: [http://127.0.0.1:3000](http://127.0.0.1:3000)

That is the main app page.

## What this start file does
`start-local.bat` starts two small local services:
- The backend at `http://127.0.0.1:8000`
- The frontend at `http://127.0.0.1:3000`

You do not need to type separate commands if `start-local.bat` works.

## If you prefer running one command yourself
From the repo root, run:
```powershell
.\start-local.bat
```

## How to stop the app
Use either of these:
- Double-click `stop-local.bat`
- Or close the two command windows named `Snowmass Backend` and `Snowmass Frontend`

## What `backend/.python` is
Right now, `backend/.python` is the local Python runtime this app is using on this computer.

That means:
- It is currently required for the one-click start flow I set up.
- It is local to this repo, so it does not need a separate system-wide Python install to run.
- It is replaceable later if you install a normal Python 3.11 setup on this computer and we switch the start flow to use that instead.

So the short version is: keep `backend/.python` for now.

## If the app does not open
1. Double-click `start-local.bat` again.
2. Check whether two command windows opened.
3. If they did, wait 5 to 10 seconds and refresh [http://127.0.0.1:3000](http://127.0.0.1:3000).
4. If one of the windows shows an error, send me that message and I can tighten the startup flow further.

## Exactly what to click next time
Next time, open this folder and double-click:
`start-local.bat`

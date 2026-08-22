# Deploying to Render.com

The app is ready to deploy -- it's already a git repository with a
`render.yaml` that tells Render exactly how to run it, including a
persistent disk so your database and uploaded photos survive every
future deploy. Here's what's already done vs. what only you can do
(account creation and payment info aren't things I can enter for you).

**Cost:** Render's free web-service tier can't attach a persistent
disk, and this app needs one (for the database and your dogs' photos)
-- so you'll need Render's **Starter** plan, currently about **$7/month**,
plus roughly **$0.25/month** for the 1 GB disk. Call it ~$7.25/month total.

## What's already done

- `webapp/` is a git repository with one commit, ready to push
- `render.yaml` -- Render reads this automatically and provisions the
  web service + a 1 GB persistent disk mounted at `/var/data`
- `requirements.txt` includes `gunicorn` (the production server)
- The app already knows how to use the disk when `DATA_DIR=/var/data`
  is set (that's wired up in `render.yaml`) -- locally, with that
  variable unset, nothing about how you run it day-to-day changes
- A safety check refuses to boot on Render with the default password

## Steps for you to do

### 1. Push the code to GitHub

If you don't already have a GitHub account, create one free at
[github.com](https://github.com). Then create a new **empty**
repository (no README, no .gitignore -- it already has one) named
something like `summit-doodles-app`. GitHub will show you a repo URL
that looks like `https://github.com/<your-username>/summit-doodles-app.git`.

Then, in Terminal:

```bash
cd "/Users/timothybroadhead/Dropbox (Personal)/Claude/Apps/SummitDoodles/webapp"
git remote add origin https://github.com/<your-username>/summit-doodles-app.git
git push -u origin main
```

The first push will ask you to sign in to GitHub in your browser --
that's normal and expected.

### 2. Create the Render service

1. Go to [render.com](https://render.com) and sign up (free to sign up;
   billing only kicks in for the Starter plan itself).
2. Click **New +** &rarr; **Blueprint**.
3. Connect your GitHub account when prompted, then pick the
   `summit-doodles-app` repository.
4. Render reads `render.yaml` and shows you the plan (Starter, ~$7/mo)
   and the disk (1 GB) it's about to create. Confirm.
5. Before it finishes, Render will ask you to fill in the
   `SUMMIT_ADMIN_PASSWORD` value (it's marked "sync: false" in the
   blueprint specifically so it prompts you instead of using a default)
   -- **pick a real password here, not `summit2026`.**
6. Click **Apply** / **Create**. Render builds and deploys -- takes a
   few minutes the first time. Watch the build log for `Live`.

### 3. Visit your app

Render gives you a URL like `https://summit-doodles.onrender.com`.
That's your real, public app -- `/apply`, `/contact`, `/puppies`, and
`/guardian` are safe to share or link to from anywhere; the dashboard
etc. need your new password.

### 4. Bring your real data over (optional)

The fresh Render deploy starts with an **empty** database -- none of
your 9 real dogs or their photos are there yet, since those only exist
in your local `instance/summitdoodles.db` and `static/uploads/`
folder (both are intentionally excluded from git so your data and
photos never end up in a public GitHub repo).

The straightforward way to move them over:
1. In the Render dashboard, open your service &rarr; **Shell** tab
   (this gives you a terminal on the live server).
2. From your own Terminal, you can copy files up with `scp` if you
   enable SSH on the service (Render's docs cover this under
   "SSH into a Render service"), or simplest: re-enter your 9 dogs and
   re-upload their photos once, directly on the live site, the same way
   you did locally -- for 9 dogs that's a quick, one-time task and
   avoids fiddling with file transfers.

Either way, come back and I can help with whichever approach you pick.

### 5. Custom domain (optional)

Render's dashboard has a **Settings &rarr; Custom Domain** section where
you can point `app.summitdoodles.com` (or similar) at it, with free
HTTPS -- worth doing once you're happy with everything.

## After the first deploy

Every future `git push` to `main` auto-redeploys the app (Render
watches the branch). Bug fixes or new features: make the change here,
I'll test it locally the way I have been, then it's just:

```bash
git add -A && git commit -m "describe the change"
git push
```

and Render picks it up automatically within a couple of minutes.

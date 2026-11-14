# Student Planner on iPhone — no Mac required

The easiest way to use the planner on an iPhone is the installable web app in [`web/`](./web/). It runs in Safari and can be added to the Home Screen; you do not need a Mac, Xcode, or the App Store. Tasks are saved in the browser on your device.

## Put it online

GitHub Pages is a free way to host this static web app:

1. Make sure the project, including the `ios/web` folder, is pushed to GitHub.
2. On the repository page, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Choose the `main` branch and **/(root)**, then click **Save**.
5. After GitHub Pages finishes publishing, open this address on your iPhone:
   `https://zofgk0227.github.io/Student_Planner/ios/web/`

If your repository uses a different owner or name, replace those parts of the address with your repository's details. GitHub Pages must be enabled and the site must be publicly accessible for this link to work.

## Install it on your iPhone

1. Open the published address in **Safari**.
2. Tap **Share** (the square with an arrow).
3. Scroll down and tap **Add to Home Screen**. If it is not shown, scroll to the bottom, tap **Edit Actions**, and add it.
4. Tap **Add**. Launch **Study Bloom** from the new Home Screen icon.

The app also works in a desktop browser for local testing, but iPhone Home Screen installation and offline support require the site to be served over HTTPS. The website stores tasks in that browser's local storage; use **Progress → Export** to make a backup, or **Import JSON** to bring in `student_planner_tasks.json` from the desktop app. The original Python planner and optional SwiftUI project are unchanged.

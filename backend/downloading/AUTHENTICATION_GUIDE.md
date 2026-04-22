# YouTube Authentication Guide

## Problem: "Sign in to confirm you're not a bot"

YouTube blocks automated requests from yt-dlp to prevent bot activity. This guide explains how to configure authentication to bypass this restriction.

## Solution: Browser Cookie Extraction

The most reliable method is to extract cookies from your web browser, which provides YouTube with a real user session.

### Method 1: Using Browser Cookies (Local Development Only)

**⚠️ IMPORTANT: This method only works for local development where a browser is running on the same machine as the server. For production servers (Render, Vercel, etc.), use Method 2 with cookies.txt file.**

#### Step 1: Configure Environment Variables

Set the following environment variables in your `.env` file or system:

```env
# For Chrome (Windows/macOS/Linux)
YT_DL_BROWSER=chrome

# For Chrome with specific profile (optional)
YT_DL_BROWSER_PROFILE=Default

# For Firefox
YT_DL_BROWSER=firefox

# For Brave
YT_DL_BROWSER=brave

# For Edge
YT_DL_BROWSER=edge

# For Safari (macOS only)
YT_DL_BROWSER=safari

# For Chromium
YT_DL_BROWSER=chromium
```

#### Step 2: Ensure Browser is Running

Make sure your browser is running and you're logged into YouTube in that browser. The cookies will be extracted from the active browser session.

#### Step 3: Restart Your Application

After setting the environment variables, restart your Django backend server.

### Method 2: Using cookies.txt File (Production Servers)

**This is the recommended method for production deployments on Render, Vercel, Railway, etc.**

If browser extraction doesn't work, you can manually export cookies:

#### Step 1: Export Cookies from Browser

**Chrome/Chromium:**
1. Install the "Get cookies.txt LOCALLY" extension
2. Go to YouTube and make sure you're logged in
3. Click the extension icon and export cookies
4. Save the file as `cookies.txt`

**Firefox:**
1. Install the "cookies.txt" add-on
2. Go to YouTube and make sure you're logged in
3. Use the add-on to export cookies
4. Save the file as `cookies.txt`

#### Step 2: Place cookies.txt File

Place the exported `cookies.txt` file in the `backend/downloading/` directory (same directory as `views.py`).

#### Step 3: Restart Your Application

Restart your Django backend server.

## Troubleshooting

### Issue: Browser cookies not working (Local Development)

**Solution:**
1. Make sure the browser is running when you start the Django server
2. Check that you're logged into YouTube in that browser
3. Verify the browser name is correct (chrome, firefox, brave, edge, safari, chromium)
4. Try using a specific profile: `YT_DL_BROWSER_PROFILE=Default`

### Issue: "cookies.txt NOT FOUND" error

**Solution:**
- Ensure the `cookies.txt` file is in the correct directory: `backend/downloading/cookies.txt`
- Check file permissions
- Verify the file has content (not empty)

### Issue: "_parse_browser_specification() takes from 1 to 4 positional arguments but 6 were given"

**Solution:**
This error occurs when yt-dlp receives an incorrect browser specification format. The code has been updated to handle this automatically.

### Issue: Still getting bot verification error

**Solution:**
1. Try a different browser
2. Clear browser cache and re-login to YouTube
3. Use a VPN if you're in a restricted region
4. Wait a few hours and try again (YouTube may temporarily block your IP)

### Issue: Production deployment (Render, Vercel, etc.) not working

**Solution:**
Production servers don't have browsers running, so browser cookie extraction won't work. You must use the cookies.txt method:
1. Export cookies from your browser locally
2. Upload the `cookies.txt` file to your production server
3. Place it in the `backend/downloading/` directory
4. Restart your production server

## Platform-Specific Notes

### Windows
- Chrome profile is usually at: `C:\Users\[Username]\AppData\Local\Google\Chrome\User Data\Default`
- Firefox profile is usually at: `C:\Users\[Username]\AppData\Roaming\Mozilla\Firefox\Profiles\`

### macOS
- Chrome profile is usually at: `~/Library/Application Support/Google/Chrome/Default`
- Safari profiles are managed automatically

### Linux
- Chrome profile is usually at: `~/.config/google-chrome/Default`
- Firefox profile is usually at: `~/.mozilla/firefox/`

## Security Considerations

- Browser cookies contain sensitive authentication data
- Keep your `.env` file secure and never commit it to version control
- The cookies are extracted at runtime and not stored permanently
- Consider using a dedicated browser profile for this purpose

## Additional Resources

- [yt-dlp documentation on cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [Exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
- [Browser cookie extraction guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#cookies-from-browser)
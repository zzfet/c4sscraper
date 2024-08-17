# C4S metadata scraper
A very janky, ropey script for pulling metadata from C4S. I threw this together after a studio I was tagging in Stash mysteriously shut up shop and disappeared. It then occurred to me that I should probably back up the other studios I'm working through in case the same thing happens again. Plus, it'd probably be good for preservation/archiving/etc.

# Here be dragons!
A quick word of warning. This script is dirty (and not just in terms of the data it scrapes!)

There are many things in this script that could very likely be done a lot more efficiently or tidily. I used a lot of ChatGPT in making this, and it probably shows.

**I am not responsible for any damage, etc. You may get blocked by C4S - I've put time delays so the script isn't hammering anything, but you never know. Maybe pop a VPN on just to be safe.**

# Default behaviour
If you choose to scrape just the metadata (i.e. not the thumbnail images), it will save a .json file in the same directory as this script named after the studio link (for example, for a studio with a link '/studio/000000/my-studio', the resulting file will be 'my-studio.json').

If you also choose to scrape the thumbnail data, the .json file will be placed in a tgz file alongside a folder called 'my-studio_thumbs'. One thing I still need to fix is that the links to the images in the .json file still point to the web versions, but this can be remedied with a find/replace.

The script also supports 'delta' updating. If you have already pulled down a studio before, and the .json/.tgz file is still next to the script, instead of pulling all data down from scratch, it will 'top up' the existing dataset instead. This is done in quite a dirty way - we go through pages until we see a clip title that's already in the json file, and halt when we hit one. So if changes are made to a really old clip, these won't be reflected in the delta. But it's something you can potentially put in a crontab if you want to keep an up-to-date JSON copy of a studio on your machine.

# Parameters
This script accepts the following parameters:\
\
**--save-images (or -S)** - If this switch is set, thumbnail images will also be saved.
**--url-list (or -L)** - Allows you to specify a text file containing a list of C4S studios (one link per line)
**url** - The URL of the studio you want to scrape (if url-list not defined)

If no parameters are passed, you are asked interactively for a URL and whether you want to save images.

# Requirements
- requests
- datetime
- re
- json
- time
- os
- argparse
- tarfile
- shutil

# License
Do whatever you like - I relinquish this into the public domain. I hope it serves as a good starting point to someone, or helps with the preservation of C4S data.

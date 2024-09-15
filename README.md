# Stack Exchange Backup

Download all your posts on the Stack Exchange network as Markdown files 
via a Python script talking to the Stack Exchange API.

## Showcase

![Program run demo](assets/demo.avif)
![Example download file](assets/markdown.png)

## Installation

1. Either download the repository as a ZIP file and extract it, 
    or [install Git](https://git-scm.com/downloads) (recommended) and do a `git clone` of the project:

    ```shell
    git clone https://github.com/9ao9ai9ar/stack-exchange-backup.git
    ```

2. [Install Python 3.12 or newer](https://www.python.org/downloads/).
    See the [support section](#support) for additional information.

3. Enter the directory you just extracted/cloned:

    ```shell
    cd stack-exchange-backup
    ```

    All steps hereafter assume operations under said directory.

4. Create and activate a virtual environment (strongly recommended).

    1. If you're on Windows and have kept the defaults when installing Python using the official installer, 
        the Python Launcher `py` should be installed alongside it, 
        and you can issue the following command in a command-line shell to create a virtual environment:
    
        ```shell
        py -3.12 -m venv .venv 
        ```
    
        Otherwise, check the Python version on your *PATH* with `python -V` and, 
        if it meets the minimum required Python version, 
        create a virtual environment by executing:
    
        ```shell
        python -m venv .venv
        ```
    
        On Linux, venv is usually in its own package separate from the Python installation, 
        in which case consult your distribution's documentation on how to install venv before proceeding.

    2. After a virtual environment has been created, you need to activate it.
        For Linux and macOS, the command is:
    
        ```shell 
        . .venv/bin/activate
        ```
    
        and for Windows it is:
    
        ```shell
        .\.venv\Scripts\activate
        ```
    
        Note that if you're using PowerShell on Windows, 
        you'd first have to enable script execution in order to activate the virtual environment:
    
        ```powershell
        Set-ExecutionPolicy -ExecutionPolicy AllSigned -Scope CurrentUser
        ```

5. Install `stack-exchange-backup` as a local Python package using pip:

    ```shell
    # Install from the requirements file first if you want reproducible build.
    python -m pip install -r requirements/prod.txt
    python -m pip install .
    ```
    
    You may have to [ensure pip is installed](https://pip.pypa.io/en/stable/installation/) because, 
    like venv, pip doesn't come bundled with Python in most Linux distributions.

In the future, I may consider publishing the program either as a package on PyPI or as a self-contained executable, 
so that the installation guide can be simpler than it already is.

## Usage

Remember to always activate the virtual environment first!

```console
(.venv) $ python -m stackexchange.backup --help
usage: backup.py [-h] --account-id ACCOUNT_ID [--no-meta] [--out-dir OUT_DIR] [--request-key REQUEST_KEY] [--rps RPS]

options:
  -h, --help            show this help message and exit
  --account-id ACCOUNT_ID
                        account ID
  --no-meta             do not back up meta posts
  --out-dir OUT_DIR     output directory (default: q_and_a)
  --request-key REQUEST_KEY
                        request key
  --rps RPS             requests per second limit (default: 20)
```

* `ACCOUNT_ID`: the ID of a Stack Exchange account.
Note that this is NOT the per-site user IDs.
To acquire the `ACCOUNT_ID` of a user:

    1. Go to the user's profile page on one of the Stack Exchange network sites 
        and click on either the *View all* link next to *Communities* 
        or the *Network profile* link in the dropdown under *Profiles*.
       
        ![Jeff Atwood's Stack Overflow user profile page](assets/network_user.png)

    2. On the new web page that is just opened, 
        note the URL segment after `users` consists of a number: 
        this is the `ACCOUNT_ID` of the user (1 in the case of Jeff Atwood).

        ![Jeff Atwood's Stack Exchange account page](assets/account_id.png)

* `OUT_DIR`: the folder to download your files to, can be either a relative path or an absolute path.

* `REQUEST_KEY`: we provide a default request key only for your convenience.
As per this [FAQ](https://stackapps.com/q/67) on Stack Apps, 
it is advisable that users [bring their own request keys](https://stackapps.com/apps/oauth/register).
To access the API without a request key, provide an empty string as the value to this option.

* `RPS`: requests per second, a soft limit imposed on the running program.
It is stated in the [docs](https://api.stackexchange.com/docs/throttle) in no uncertain terms that 
the Stack Exchange API considers 30+ requests per second per IP to be very abusive, 
and will thus ban any rogue IP from making further requests to the API for an indefinite period of time.
Due to the nature of floating-point arithmetic and the limitations of the current implementation, 
do not assume it is an exact upper bound on the number of requests the program will make within any one-second period.

## Format

**NOTE:** The output directory structure, filenames as well as the Markdown content layout format, 
are still subject to change without prior notice.
If the output format is modified, this README will be updated to reflect the changes.

The output directory has the following structure:

```console
+---<stack exchange site 1 hostname>
|   +---answers
|   |       <question id associated with answer 1 id>.md
|   |       <question id associated with answer 2 id>.md
|   |       ...
|   |
|   \---questions
|           <question 1 id>.md
|           <question 2 id>.md
|           ...
|
+---<stack exchange site 2 hostname>
|   +---answers
|   |       <question id associated with answer 1 id>.md
|   |       <question id associated with answer 2 id>.md
|   |       ...
|   |
|   \---questions
|           <question 1 id>.md
|           <question 2 id>.md
|           ...
|
...
```

Each Markdown file will represent either a question or an answer, 
depending on whether it is under a `questions` directory or an `answers` directory.
If the Markdown file represents a question, then the question creator will be you.
Otherwise, if the Markdown file represents an answer, the question creator will not be you, 
but the creator of one of the answers included in the Markdown file will be you.
More specifically, each Markdown file will have the following format 
(text that is inside angle brackets, such as `<this>`, represents text that will vary for each Markdown file):

```markdown
Question downloaded from <question link>
Question asked by <username for question creator> on <question date> at <question time>.
Number of up votes: <number of up votes for question>
Number of down votes: <number of down votes for question>
Score: <overall score associated with the question (number of up votes - number of down votes)>

# <question title>
<question body>

<loop through 1 to i if there are comments for the question>

### Comment <i>
Comment made by <username for comment i creator> on <comment i date> at <comment i time>.
Comment score: <number of up votes for comment i>

<comment i body>

<loop through 1 to j if there are answers for the question>

## Answer <j>
Answer given by <username for answer j creator> on <answer j date> at <answer j time>.
This <is/is not> the accepted answer.
Number of up votes: <number of up votes for answer j>
Number of down votes: <number of down votes for answer j>
Score: <overall score associated with answer j (number of up votes - number of down votes)>

<answer j body>

<loop through 1 to k if there are comments for answer j>

### Comment <k>
Comment made by <username for comment k creator> on <comment k date> at <comment k time>.
Comment score: <number of up votes for comment k>

<comment k body>
```

## FAQ

1. ***Are deleted posts included in the backup?***

   **No.**
   [The public API does not provide a way to retrieve deleted posts](https://stackapps.com/q/1917), 
   even when authenticated.

2. ***Are favorites/bookmarks/saves included in the backup?***

   **No.**
   When public favorites, also briefly known as bookmarks, got reworked into private saves, 
   it was done without coordinated changes to the API, 
   so [it became impossible to query a user's saves through the API](https://meta.stackexchange.com/q/382991).

3. ***Are Area 51 posts included in the backup?***

   **No.**
   [Area 51 is not adequately supported in the API](https://stackapps.com/q/8726),
   and very few people are affected by this lack of support.

4. ***Are articles included in the backup?***

   **No.**
   Being a part of collectives, articles are only supported on Stack Overflow,
   and fewer than 100 articles have been published to date since the beta release of collectives in 2021.
   Therefore, I have concluded it's not worth the effort to add support for backing up articles,
   despite them still being queryable through the `/users/{ids}/posts` endpoint
   after [`/articles` has been removed from the public API](https://stackapps.com/a/10466).

## Related Projects

### [Stack Exchange API](https://api.stackexchange.com/)

#### [mhdadk/stack-exchange-backup](https://github.com/mhdadk/stack-exchange-backup)

The original repository from which this fork is derived.
I'd like to express my thanks to its author, Mahmoud Abdelkhalek, 
for his well-commented code expedited my process of grokking the Stack Exchange API, which, 
while conceptually simple, has its documentation of related topics,
some insufficiently explained, and the numerous bugs scattered all over the place.

#### [StackExchangeBackupLaravel](https://github.com/ryancwalsh/StackExchangeBackupLaravelPHP)

StackExchangeBackupLaravel allows exporting a somewhat complete data footprint of a user on the Stack Exchange network, 
but the outputs are in JSON rather than Markdown, which are also zipped and uploaded to Amazon S3 by default.
By contrast, Stack Exchange Backup is simple and straightforward: everything is downloaded to the local machine only,
and installation is easier and documentation more thorough.

### [Stack Exchange Data Explorer](https://data.stackexchange.com/)

The Stack Exchange Data Explorer (SEDE) is an open source tool 
for running arbitrary queries against public data from the Stack Exchange network.
There are ready-made queries to back up your posts on the Stack Exchange network either as a 
[single HTML file](https://data.stackexchange.com/meta.stackexchange/query/758326) 
or as a [CSV file](https://data.stackexchange.com/meta.stackexchange/query/1529864).
Unfortunately, they are not the one-stop solutions to outputting individual source files in the Markdown format.
Moreover, to use the SEDE service, you'd either have to log in or solve some CAPTCHAs first, 
and [the data is only updated weekly](https://data.stackexchange.com/help#faq), 
as opposed to the data returned by the API, [which is updated about once a minute](https://stackapps.com/a/3544).

#### [Pippim Website](https://www.pippim.com/programs/stack.html)

Converts your Stack Exchange posts to your own website, hosted for free on GitHub Pages.
Requires you to manually run the aforementioned SEDE query that outputs as a CSV file beforehand.

### [Stack Exchange Data Dump](https://stackoverflow.com/help/data-dumps)

This is a quarterly dump of all user-contributed data on the Stack Exchange network.
In an [announcement](https://meta.stackexchange.com/q/401324) made in July 2024, 
the data dumps will no longer be uploaded to the [Internet Archive](https://archive.org/details/stackexchange); 
instead, they will be provided from a section of the site user profile on a Stack Exchange profile.
Therefore, this method of backup has a few major downsides:

1. Being locked behind a login wall.
2. Being incomplete, meaning the data dump you download 
    are only for the specific site from which you initiated the request.
3. Being complete, meaning that the download size may be humongous, and to get only your data, 
    you'd have to do some non-trivial parsing of the downloaded XML files yourself.

Thankfully, there exists the 
[Stack Exchange data dump downloader and transformer](https://github.com/LunarWatcher/se-data-dump-transformer)
project that aims to overcome these pain points.

## Development

In addition to the `dev` dependencies, this project relies on the following tools: 

* [uv](https://github.com/astral-sh/uv) (install standalone executable)
* [security-constraints](https://github.com/mam-dev/security-constraints) (`uv tool install security-constraints`)
* [Pyright](https://github.com/microsoft/pyright) 
(`npm install pyright` after [installing Node.js](https://nodejs.org/en/download))

Before each commit, you should run the appropriate `release` script for your shell.

To help you in your experimentation with the Stack Exchange APIs through the documentation webpages, 
I have compiled a list of the parameter types and their associated icons as below:

* ![string-type](https://cdn.sstatic.net/apiv2/img/text.png): Strings
* ![number-type](https://cdn.sstatic.net/apiv2/img/number.png): 
[Numbers](https://api.stackexchange.com/docs/numbers)
* ![date-type](https://cdn.sstatic.net/apiv2/img/calendar.png): 
[Dates](https://api.stackexchange.com/docs/dates)
* ![list-type](https://cdn.sstatic.net/apiv2/img/list.png): 
[Lists](https://api.stackexchange.com/docs/vectors)
* ![key-type](https://cdn.sstatic.net/apiv2/img/key.png): 
[Keys](https://api.stackexchange.com/docs/authentication)
* ![access-token-type](https://cdn.sstatic.net/apiv2/img/access-token.png): 
[Access Tokens](https://api.stackexchange.com/docs/authentication)

Except for numbers and dates, the icons are not explained anywhere in the documentation, 
but if you open the inspector in your web browser, 
say when you're on [this page](https://api.stackexchange.com/docs/edit-question), 
and check the `<input>` nodes, you'll see that the `class` attributes include `string-type`, `number-type`, etc., 
which give you enough hint of how they should be inputted.

## Support

It is my policy to strive to support all 
[non-end-of-life stable releases](https://devguide.python.org/versions/#status-key) of Python.
However, indispensable features I rely on are sometimes not supported on older Python versions without backporting.
Therefore, I can only promise my code will run on the latest bugfix release of Python.
If you are a Windows user and wants to use an older, supported Python release, 
do note that the official website does not provide binaries for the security releases. 
Thereby, I encourage you to instead install it through one of the following conda distributions or package managers 
to benefit from the continuing security fixes:

* [Miniconda](https://docs.anaconda.com/miniconda/)
* [Miniforge](https://github.com/conda-forge/miniforge)
* [Micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
* [Pixi](https://pixi.sh/latest/)

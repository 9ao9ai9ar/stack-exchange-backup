# Stack Exchange Backup

Download all your posts on the Stack Exchange network as Markdown files
via a Python script talking to the Stack Exchange API.

## Showcase

![Program run demo](assets/demo.avif)
![Example download file](assets/markdown.png)

## Installation

1. Either download the repository as a ZIP file and extract it,
   or [install Git](https://git-scm.com/downloads) (recommended) and do a `git clone` of the project.

   ```shell
   git clone https://github.com/9ao9ai9ar/stack-exchange-backup.git
   ```

2. [Install Python 3.12 or newer](https://www.python.org/downloads/).
   See the [support section](#support) for additional information.

3. Enter the directory you just extracted/cloned.

   ```shell
   cd stack-exchange-backup
   ```

   All steps hereafter assume operations under said directory.

4. Create and activate a virtual environment (strongly recommended).

    * Windows:

      ```shell
      py -3 -m venv .venv
      .\.venv\Scripts\activate
      ```

    * macOS/Linux:

       ```shell
       python3 -m venv .venv
       . .venv/bin/activate
       ```

5. Install `stack-exchange-backup` as a local Python package.

   ```shell
   python -m pip install -r ./requirements.txt
   python -m pip install .
   ```

## Usage

Remember to activate the virtual environment first!

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

* `ACCOUNT_ID`: the ID of the Stack Exchange account whose posts you want to back up.
  Note that this is NOT the per-site user ID.
  To acquire the `ACCOUNT_ID` of a user:

    1. Go to the user's profile page on one of the Stack Exchange network sites
       and click on either the *View all* link next to *Communities*
       or the *Network profile* link in the dropdown under *Profiles*.

       ![Jeff Atwood's Stack Overflow user profile page](assets/network_user.png)

    2. On the new web page that is just opened, note the URL segment after `users` consists of a number:
       this is the `ACCOUNT_ID` of the user (1 in the case of Jeff Atwood).

       ![Jeff Atwood's Stack Exchange account page](assets/account_id.png)

* `OUT_DIR`: the folder to download your files to.

* `REQUEST_KEY`: a token that grants an increased download quota.
  We provide a default request key only for your convenience.
  As per this [FAQ](https://stackapps.com/q/67),
  it is advisable that users [bring their own request keys](https://stackapps.com/apps/oauth/register).
  To access the API without a request key, assign an empty string as the value to this option.

* `RPS`: requests per second, a soft limit imposed on the running program.
  It is stated [in no uncertain terms](https://api.stackexchange.com/docs/throttle) that
  the Stack Exchange API considers 30+ requests per second per IP to be very abusive,
  and will thus ban any rogue IP from making further requests to it for an indefinite period of time.
  Due to the nature of floating-point arithmetic and the limitations of the current implementation,
  do not assume it is an exact upper bound on the number of requests the program will make within any one-second period.

## Output

> [!WARNING]  
> A new output layout is underway.
> This section will be updated when the design is finalized and pushed.

### Directory Layout

```console
<OUT_DIR>
+---<stack exchange site 1 domain name>
|   +---answers
|   |       <question id associated with answer 1>.md
|   |       <question id associated with answer 2>.md
|   |       ...
|   |
|   \---questions
|           <question 1 id>.md
|           <question 2 id>.md
|           ...
|
+---<stack exchange site 2 domain name>
|   +---answers
|   |       <question id associated with answer 1>.md
|   |       <question id associated with answer 2>.md
|   |       ...
|   |
|   \---questions
|           <question 1 id>.md
|           <question 2 id>.md
|           ...
|
...
```

### File Layout

```markdown
Question downloaded from <question link>
Question asked by <username of question creator> on <question date> at <question time>.
Number of up votes: <number of up votes for question>
Number of down votes: <number of down votes for question>
Score: <overall score associated with question (number of up votes - number of down votes)>

# <question title>

<question body>

<loop through 1 to i if there are comments to question>

### Comment <i>

Comment made by <username of comment i creator> on <comment i date> at <comment i time>.
Comment score: <number of up votes for comment i>

<comment i body>

<loop through 1 to j if there are answers to question>

## Answer <j>

Answer given by <username of answer j creator> on <answer j date> at <answer j time>.
This <is/is not> the accepted answer.
Number of up votes: <number of up votes for answer j>
Number of down votes: <number of down votes for answer j>
Score: <overall score associated with answer j (number of up votes - number of down votes)>

<answer j body>

<loop through 1 to k if there are comments to answer j>

### Comment <k>

Comment made by <username of comment k creator> on <comment k date> at <comment k time>.
Comment score: <number of up votes for comment k>

<comment k body>
```

### Omissions

| Item          | Reason                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deleted posts | [The API does not provide a way to retrieve deleted posts](https://stackapps.com/q/1917), even when authenticated.                                                                                                                                                                                                                                                                                                                                                       |
| Saves         | When public favorites, also briefly known as bookmarks, got reworked into private saves, it was done without coordinated changes to the API, so [it became impossible to query a user's saves through the API](https://meta.stackexchange.com/q/382991).                                                                                                                                                                                                                 |
| Area 51 posts | [Area 51 is not adequately supported in the API](https://stackapps.com/q/8726), and few people participated on this site.                                                                                                                                                                                                                                                                                                                                                |
| Articles      | Being a part of collectives, articles have only been rolled out to Stack Overflow, and fewer than 200 articles have been [published](https://stackoverflow.com/collectives/articles) to date since release. Therefore, I have concluded it's not worth the effort to add support for backing up articles, despite them still being queryable through the `/users/{ids}/posts` endpoint after [`/articles` has been removed from the API](https://stackapps.com/a/10466). |

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
but the output files are in JSON rather than Markdown, which are also zipped and uploaded to Amazon S3 by default.
By contrast, Stack Exchange Backup is simple and straightforward:
everything is downloaded to the local machine only, and installation is easier and documentation more thorough.

### [Stack Exchange Data Explorer](https://data.stackexchange.com/)

The Stack Exchange Data Explorer (SEDE) is an open source tool
for running arbitrary queries against public data from the Stack Exchange network.
There are ready-made queries to export your data to a
[single HTML file](https://data.stackexchange.com/meta.stackexchange/query/758326)
or a [CSV file](https://data.stackexchange.com/meta.stackexchange/query/1529864).
Unfortunately, they are not the one-stop solution to output individual Markdown files as they were originally authored.
Moreover, to use the SEDE service, you'd either have to log in or solve some CAPTCHAs first,
and the data is only [refreshed weekly](https://data.stackexchange.com/help#faq),
as opposed to the data returned by the API, which is [refreshed about once a minute](https://stackapps.com/a/3544).

#### [Pippim Website](https://www.pippim.com/programs/stack.html)

This is a demo website that comes with a set of procedures and programs to help
convert your Stack Exchange posts into a fancy GitHub Pages website.

### [Stack Exchange Data Dump](https://stackoverflow.com/help/data-dumps)

This is a quarterly dump of all user-contributed data on the Stack Exchange network.
In an [announcement](https://meta.stackexchange.com/q/401324) made in July 2024,
the data dumps will no longer be uploaded to the [Internet Archive](https://archive.org/details/stackexchange);
instead, they will be provided from a section in the site user profile settings.
Therefore, this method of backup has a few major downsides:

1. Being locked behind a login wall.
2. Being incomplete, meaning the data dump you download
   is only for the specific site from which you initiated the request.
3. Being complete, meaning the download size may be humongous, and to get only your data,
   you'd have to do some non-trivial parsing of the downloaded XML files yourself.

#### [Stack Exchange data dump downloader and transformer](https://github.com/LunarWatcher/se-data-dump-transformer)

Thankfully, this project exists to address some of the above pain points.

## Development

My personal development process for this project is encoded in `release.ps1`,
a polyglot script that is valid in both the Bourne shell and PowerShell.
In addition to the dependencies specified in `pyproject.toml`, the script relies on the following utilities:

* [uv](https://github.com/astral-sh/uv)
* [security-constraints](https://github.com/mam-dev/security-constraints)
* [Pyright](https://github.com/microsoft/pyright)

which need to be installed and configured separately as instructed in the comments therein.

To help you in your experimentation with the Stack Exchange API through the documentation web pages,
I have compiled a list of the parameter types and their associated icons as follows:

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
and check the `<input>` nodes enclosing the icons you're interested in learning about,
you'll find that the parameter types are named in the `class` attributes, as `string-type`, `number-type`, etc.

## Support

It is my policy to strive to support, within reason,
all [non-end-of-life, stable releases](https://devguide.python.org/versions/#status-key) of Python,
as well as all prominent, up-to-date Python implementations, namely CPython, PyPy and GraalPy.
If you are a Windows or macOS user, do note that official binaries are not provided for the security releases.
Thereby, I encourage you to instead install it through one of the following channels
to benefit from the continuing security fixes:

* [Miniconda](https://docs.anaconda.com/miniconda/)
* [Miniforge](https://github.com/conda-forge/miniforge)
* [Micromamba](https://github.com/mamba-org/mamba#micromamba)
* [Pixi](https://github.com/prefix-dev/pixi)

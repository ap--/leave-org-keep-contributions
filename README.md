# Leave Org Keep Contributions

When you are about to leave an organisation and you want to keep your
contributions, there's a bunch of things you'll have to do to before
leaving so that you can keep all of your green squares in your contribution
graph.


## TL;DR

If organisation repository is public:

- [ ] Repository must be starred

If organisation repository is private:

- [ ] Repository must be starred
- [ ] You must be the author of an issue or a pr in the repo


## How do I find all of my contributions in my org?

I was wondering the same thing, and wanted to make sure that I won't
forget something. So I put together this script that checks all repositories
that you can access in a given organisation, and checks if you've contributed,
if you've opened issues and if you've created pull requests. I put this
together super quickly, so that it gets the job done. If you'd like to clean
it up and or improve it, please open an issue or pr!

To run the script, get a [classic personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) (the graphql api required a
classic token) and export it as `GH_TOKEN` or provide it via the command line
argument `--token` or store it to a file and use `--token-file`.

So let's assume your github username is `myuser` and you're leaving the
`myorg` organisation. Then run:


```shell
python keep-contributions.py --token '<your PAT token>' myorg myuser --scan
```

Dependent on how big the organisation is this will take a while. But don't
worry: This entire script has not been optimized at all and runs slow enough
that you won't run into rate-limiting issues :smiley: The output will look
somewhat like this:

```shell
ContributionInfo(name='myorg/somerepo', is_private=False, user='ap--', has_commits=True, is_starred=False, is_issue_author=True, is_pr_author=False)
ContributionInfo(name='myorg/another-repo', is_private=True, user='ap--', has_commits=True, is_starred=False, is_issue_author=False, is_pr_author=False)
ContributionInfo(name='myorg/one-more-repo', is_private=True, user='ap--', has_commits=True, is_starred=True, is_issue_author=False, is_pr_author=True)
```

Once it's finished you can run the same command without `--scan`

```shell
python keep-contributions.py --token '<your PAT token>' myorg myuser
```

And it'll display the required information about all repositories that you
have contributed to.

```shell
# STATUS private commits stars issue prs repository
 WARN    .       .       !!    .     !!  myorg/somerepo
 WARN    !!      .       !!    !!    !!  myorg/another-repo
         !!      .       .     !!    .   myorg/one-more-repo
```

If repositories you contributed to don't meet the requirements for your contributions to be counted
after leaving, the script will show a warning.


## Links

- [how to show private contributions](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/managing-contribution-settings-on-your-profile/showing-your-private-contributions-and-achievements-on-your-profile)
- [when are contributions counted](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/managing-contribution-settings-on-your-profile/why-are-my-contributions-not-showing-up-on-my-profile#commits)
- [comment about stars/issues/prs in private repos](https://github.com/isaacs/github/issues/1138#issuecomment-873645874)


## Contributing

Let me know if this was useful to you, by starring this repo, and let me know
if there's any mistakes, or if this needs to be updated!


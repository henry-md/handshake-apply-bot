"""
LLM prompt to generate query keywords:

I'm trying to make a bot to apply to jobs, but I don't want to apply to every job. Please come up with a list of keywords to search on (case insensitive, but answer in lower case for neatness) so that I will apply for the job if that string is a substring anywhere in the title of the application. To help you do this, I've scraped the first 1000 jobs that come up when I search “software engineer” on the job site. I'm a software engineer looking to apply for SWE roles primarily, but also maybe to devOps or machine learning roles. However, make sure that your list doesn't have too many false positives. For example, engineer wouldn't be the best word because there are so many types of engineers that I will end up applying to a lot of jobs that I don't want. I will apply to the job if ANY of the words show up ANYWHERE in the title. Please give me a list of keywords — I'll paste the list below.

Note: Jobs will be applied to that have at least 1 match in query_keywords AND exactly 0 matches in bad_keywords.
"""

query_keywords = \
    ['software',
     'developer', 
     'devops', 
     'backend', 
     'frontend', 
     'fullstack', 
     'full-stack',
     'full stack',
     'react',
     'python',
     'java',
     'node',
     'angular',
     '.net',
     'android',
     'ios',
     'mobile',
     'web',
     'cloud',
     'machine learning',
     'ml engineer',
     'ai engineer',
     'ai solutions',
     'artificial intelligence',
     'nlp',
     'data engineer',
     'data science',
     'data scientist',
     'reliability engineer',
     'test engineer',
     'algorithm',
     'swe',
     'sde',
     'programmer',
     'security',
     'coding',
     'application',
     'embedded',
     'mean stack',
     'mern stack',
    ]

bad_keywords = [
    'intern',
    'unpaid',
    'not paid',
    'part time',
    'part-time',
]

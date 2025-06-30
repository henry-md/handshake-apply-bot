"""
LLM prompt to generate query keywords:

I'm trying to make a bot to apply to jobs, but I don't want to apply to every job. Please come up with a list of keywords to search on (case insensitive, but answer in lower case for neatness) so that I will apply for the job if that string is a substring anywhere in the title of the application. To help you do this, I've scraped the first 1000 jobs that come up when I search “software engineer” on the job site. I'm a software engineer looking to apply for SWE roles primarily, but also maybe to devOps or machine learning roles. However, make sure that your list doesn't have too many false positives. For example, engineer wouldn't be the best word because there are so many types of engineers that I will end up applying to a lot of jobs that I don't want. I will apply to the job if ANY of the words show up ANYWHERE in the title. Please give me a list of keywords — I'll paste the list below.

Note: Jobs will be applied to that have at least 1 match in all levels of good_keywords AND exactly 0 matches in bad_keywords.
"""

# What will be typed in Handshake's search bar to find jobs
query_search = "software engineer internship"

# Keywords to search for in job titles
good_keywords = {
    # Require 'intern' or 'internship'
    # 'intern': [
    #     'intern',
    #     'summer',
    # ],
    # Require SWE job
    'swe': [
        'software',
        'developer', 
        'devops', 
        'frontend', 
        'front-end',
        'front end',
        'backend',
        'back-end',
        'back end',
        'fullstack', 
        'full-stack',
        'full stack',
        'react',
        'python',
        'java',
        'node',
        'angular',
        '.net',
        'c++',
        'c#',
        'nodejs',
        'node.js',
        'postman',
        'sql',
        'mongodb',
        'nosql',
        'nosql',
        'database',
        'android',
        'ios',
        'mobile',
        'web',
        'cloud',
        'machine learning',
        'ml engineer',
        'ai',
        'ml',
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
        'mean-stack',
        'mern stack',
        'mern-stack',
        'computer vision',
        'computer-vision',
        'computer science',
    ]
}

bad_keywords = [
    # 'unpaid',
    'not paid',
    'unpaid',
    'instructor',
    'teacher',
    'teaching',
]

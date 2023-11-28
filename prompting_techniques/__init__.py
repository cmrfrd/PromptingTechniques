import asyncio
import functools
import inspect
import shelve
from functools import partial, wraps

import anyio
import tqdm
import typer


class AsyncTyper(typer.Typer):
    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)
        def add_runner(f):            
            @wraps(f)
            def runner(*args, **kwargs):
                func = partial(f, *args, **kwargs)
                return anyio.run(func)
            if inspect.iscoroutinefunction(f):
                return decorator(runner)
            return decorator(f)
        return add_runner

def format_prompt(prompt: str) -> str:
    lines = prompt.split('\n')
    stripped_lines = [line.lstrip() for line in lines]
    return '\n'.join(stripped_lines)

async def wrap_awaitable(i, f):
    return i, await f

async def execute(tasks, desc="Executing tasks") -> list:
    ifs = [wrap_awaitable(i, f) for i, f in enumerate(tasks)]
    bar = tqdm.tqdm(total=len(tasks), desc=desc)
    res = []
    for f in asyncio.as_completed(ifs):
        res.append(await f)
        bar.update(1)
    return [i for _, i in sorted(res)]

def async_disk_cache(filename='./data/cache.db'):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = (func.__name__, args, frozenset(kwargs.items()))
            key = str(key)

            with shelve.open(filename) as db:
                if key in db:
                    return db[key]
                else:
                    result = await func(*args, **kwargs)
                    db[key] = result
                    return result
        return wrapper
    return decorator
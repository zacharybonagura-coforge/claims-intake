## Cursor Usage Experience

I used Cursor during this assignment with the four git worktrees under .worktrees/ (`build-api-routes`, `test-api-routes`, `dockerfile`, `readme`) and merged each into one ship branch. The one worktree I would like to talk about was `test-api-routes`. 

I used Cursor to write HTTP integration tests in `tests/integration/test_routes.py`. The job was to use `POST /notifications` through the FastAPI app, not by calling `submit_notification` directly. Cursor made a test suite that covered an accepted notice, one refusal per rule, a parse failure, and all three policy-lookup reasons. Assert status, `code`, and the `detail` values to check refusal.

## How it helped

Cursor already knew the contract mapping and the payloads from `test_validation.py`. It drafted a `TestClient` fixture that replaces the module-level `policy_client` and `repository` so tests do not share state. It parametrized rule refusals and lookup failures (`timeout`  / `unreachable` / `unparsable`). When I asked to cover an extra field on parse failure, it explained that `extra="forbid"` does not go through `missing_fields`; the handler puts that under `detail["errors"]`. The test shape followed from code I already had, not from inventing new rules.

## What it made easy

Once it created the the fixture, adding another 422 case was a row in `@pytest.mark.parametrize`. It kept assertions to `status_code`, `code`, and a few `detail` keys instead of copying the whole envelope. It also built the whole structure of the file to ensure I covered all codes incouding 201, 4xx, 409, and 5xx.

## What it made awkward

Cursor does not share my terminal, so when I tried to use pytest I got many errors. It said `PYTHONPATH=src pytest` as if I were already in the inner `claims-intake` directory to run pytest rather than giving the proper `uv` command. I was in `.worktrees/test-api-routes`, so `src` was `claims-intake/src` and pytest never found `claims`. The worktree has no `.venv`; httpx and pytest lived in the main checkout’s venv. FastAPI 0.103’s `TestClient` still passes `app=` into httpx; current httpx 0.28 removed that, so I got `Client.__init__() got an unexpected keyword argument 'app'` until I used the correct `httpx` module version. Merging the branch into ship failed because I had uncommitted edits to the same `test_routes.py` on ship. Cursor was able to describe `git restore` and `git merge`, but it did not see that I am in the wrong worktree with a messed up file.

## When I would use it

To draft the first `TestClient` module and the parametrize tables from the contract. I would not let it “run the tests” for me, because it correctly declared passing tests instead of actually running them. I instead ran pytest in a directory with the venv I actually installed, after I have merged `routes.py` into that worktree.
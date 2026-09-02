# F.A.N. environment provisioning

## Supported hosts

The provisioning contract intentionally supports a narrow host matrix:

- Windows 11 with WSL2 and Ubuntu 24.04 LTS on x86_64 (primary development host);
- native Ubuntu 24.04 LTS on x86_64 (development or future server foundation).

Other Linux distributions, WSL1, other Ubuntu releases, and non-x86_64 hosts are
outside this task. Production deployment, public networking, TLS, reverse
proxies, production secrets, CI/CD, and Kubernetes are also outside it.

The Linux scripts are shared between WSL and native Ubuntu. No Linux or
application script depends on a Windows drive letter, username, or checkout
location.

## Clean Windows 11 flow

The Windows bootstrap handles host prerequisites only. Run it from an elevated
Windows PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\bootstrap\windows.ps1
```

It defaults to **No** at the confirmation prompt. `-Yes` is the explicit
non-interactive confirmation.

The bootstrap:

1. verifies Windows 11, administrator rights, and WinGet;
2. installs Git for Windows and Windows Terminal if absent;
3. updates/enables WSL and makes WSL2 the default;
4. installs Ubuntu 24.04 using `wsl --install --location`;
5. verifies a non-root Linux user and systemd;
6. verifies NVIDIA visibility in Windows and WSL without installing a driver.

Use an explicit external data root when desired:

```powershell
.\bootstrap\windows.ps1 -DataRoot 'D:\DevInfra\WSL'
```

An explicit `-DataRoot` always wins and may point to any desired drive. When it
is omitted, the bootstrap uses `D:\DevInfra\WSL` only when `D:` is a usable
non-system filesystem drive. It does not guess among other secondary drives. If
the preferred Development drive is unavailable or unusable, it falls back to
`%LOCALAPPDATA%\FAN\WSL`, prints a warning, and explains that `-DataRoot` must be
supplied to place WSL elsewhere. An existing non-empty target directory is never
overwritten.

Installing WSL components can require a reboot. Exit code `10` means the
components were enabled and Windows must restart. Reboot and rerun the exact
command; no reboot-complete flag is used.

A fresh Ubuntu distribution uses the supported one-time interactive user
initialization. Exit code `20` prints the exact `wsl -d ...` command. Create the
Linux user, exit the distro, and rerun the bootstrap.

### Reusing an existing WSL VHD

If an `ext4.vhdx` survived a Windows reinstall and is not registered, reuse it
in place rather than importing a copy:

```powershell
.\bootstrap\windows.ps1 `
  -DistroName FAN-Ubuntu `
  -ExistingVhdPath 'D:\DevInfra\WSL\Ubuntu-24.04\ext4.vhdx' `
  -ExistingLinuxUser 'developer'
```

The script uses `wsl --import-in-place`; it does not copy, replace, or delete the
VHD. If the retained username is not provided, exit code `21` explains how to
set the default user with the supported `wsl --manage ... --set-default-user`
command. A registered distro is never overwritten by an import.

### Repository placement

The physical WSL VHD may live on `D:` or another data drive while the checkout
remains in the Linux filesystem:

```bash
mkdir -p ~/Development
cd ~/Development
git clone https://github.com/strupsts/FAN.git
cd FAN
make provision
```

This distinction matters: `~/Development/FAN` lives inside the external WSL
VHD and performs substantially better than `/mnt/c/...` or `/mnt/d/...` for
`npm ci`. Mounted-drive checkouts remain supported and receive a warning.

## Native Ubuntu 24.04 flow

Clone into a normal Linux path and run either the full development profile or
the server foundation:

```bash
git clone https://github.com/strupsts/FAN.git
cd FAN
make provision PROFILE=dev

# Or: backend + Docker host foundation, without frontend, ML, or deployment.
make provision PROFILE=server
```

The server profile is only a compatible machine foundation. It is not a
production deployment.

## Commands and profiles

```bash
make provision                 # PROFILE=dev by default
make provision PROFILE=backend # system Python, uv, backend only
make provision PROFILE=server  # backend and Docker foundation
make provision YES=1           # explicit automation confirmation
make doctor                    # read-only; no confirmation
make doctor PROFILE=server
make dev                       # verify, then start; never installs
```

`make setup` remains as a compatibility alias for backend-only locked
provisioning and still asks for confirmation.

The development stages are preflight, Ubuntu packages, Python/uv, backend,
Node/npm, frontend, Docker, PostgreSQL/migrations, ML/model, and final doctor.
Each stage verifies current facts before deciding whether to mutate anything.
The run stops at the first failed stage.

Provisioning logs and outcome history live under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/fan/provision/
```

Logs are diagnostic history only. They are never used to skip checks and do not
contain environment values or secrets.

## Idempotency and partial failures

The provisioner has no global “already succeeded” flag. Examples of its factual
checks include package-manager state, executable versions, lock hashes plus
installed-package validation, Docker daemon/Compose calls, container health,
CUDA visibility, and the exact cached model revision.

If a later stage fails:

1. completed stages remain usable;
2. dependent stages do not run;
3. the failed stage and reason are printed;
4. fix the external cause and run the same command again;
5. earlier stages re-check and converge/skip;
6. another run performs no duplicate configuration.

`make provision-test` exercises this failure/rerun/third-run behavior and the
stale-virtual-environment detector.

## Python backend and moved virtual environments

`backend/pyproject.toml`, `backend/.python-version`, and `backend/uv.lock` are
authoritative. Provisioning uses `uv sync --locked --extra dev` into
`backend/.venv`.

A Python virtual environment is not portable across checkout paths. The
provisioner validates both `sys.prefix` and executable launcher shebangs. If the
exact repository `backend/.venv` is proven stale or non-portable, it is moved to
a recoverable sibling such as:

```text
backend/.venv.invalid-20260902T010203Z
```

Then a clean environment is synchronized from the lock. Provisioning never
repairs shebangs with path string replacement and refuses to replace a symlinked
or unexpected path.

## Node and frontend

`.nvmrc` is the single Node version source (`24.18.0`). The checked-in frontend
package metadata declares npm `11.16.0`, and `package-lock.json` pins the entire
dependency graph. Provisioning installs the pinned nvm release from its official
Git repository, selects `.nvmrc`, and runs `npm ci` only when the installed tree
does not match the lock and factual `npm ls` validation.

No global Angular, Ionic, or Capacitor packages are required.

## Docker and PostgreSQL

The project accepts either:

- a working Docker Desktop WSL integration; or
- Docker Engine plus the Compose plugin installed on Linux from Docker's
  official Ubuntu apt repository.

If Docker Desktop integration is detected but its daemon is unavailable,
provisioning stops and asks the developer to start/enable that integration. It
does not install a competing Linux daemon. A working existing Docker
installation is not replaced.

PostgreSQL remains major version 16 and is pinned to
`postgres:16.15-bookworm`. Normal provisioning may pull the image, start the
service, wait for health, and apply forward-only Alembic migrations. It never
removes Compose volumes, clears schemas, or resets data. `make dev-down` can
stop/remove the container while the doctor still recognizes the retained image
and volume as prepared.

## ML runtime, GPU, and model cache

The ML runtime is deliberately independent from the FastAPI environment:

```text
backend/.venv                 backend only
$HOME/.venvs/fan-vllm         vLLM/Torch/Transformers only
```

`ml-runtime/pyproject.toml` and `ml-runtime/uv.lock` capture the known-working
runtime. The critical authoritative versions are:

| Component | Version |
| --- | --- |
| Python | 3.12 |
| vLLM | 0.22.1 |
| PyTorch | 2.11.0 (CUDA 13.0 wheel) |
| TorchVision | 0.26.0 |
| TorchAudio | 2.11.0 |
| FlashInfer | 0.6.11.post2 |
| Transformers | 5.12.0 |

Known-working transitive versions are constrained in the ML project rather
than opportunistically upgraded. Provisioning does not install a system CUDA
toolkit. On WSL it never installs an NVIDIA Linux display driver: the supported
prerequisite is a compatible Windows NVIDIA driver.

Diagnostics distinguish two failure classes:

- `nvidia-smi` unavailable: host/WSL GPU visibility; verify the Windows driver
  and try a clean `wsl --shutdown`;
- host GPU visible but `torch.cuda.is_available()` false: pinned ML runtime or
  configuration problem.

The model identity and successful immutable Hugging Face snapshot are declared
in `ml-runtime/model.env`:

```text
Qwen/Qwen2.5-VL-7B-Instruct-AWQ
536a35794df8831aa814970ee8f89eff577e7718
```

Weights remain disposable external data. An empty cache is recovered with a
normal pinned snapshot download. Defaults are XDG/home-relative under
`$HOME/.cache/fan`; use an external path without changing project files:

```bash
FAN_CACHE_DIR=/data/fan-cache make provision
```

Persistent non-secret per-user overrides may be placed in
`${XDG_CONFIG_HOME:-$HOME/.config}/fan/environment`, for example:

```bash
FAN_CACHE_DIR="$HOME/.cache/fan"
VLM_VENV="$HOME/.venvs/fan-vllm"
```

This file is sourced as user-owned shell configuration. Do not put secrets in
it. `backend/.env` remains the application settings file: provisioning never
creates or overwrites it, never logs it, and `backend/.env.example` documents
safe local defaults. The application can run with its equivalent built-in
defaults when `.env` is absent.

## Android (optional)

Core backend/frontend/VLM provisioning does not require Android Studio. The
checked-in Gradle/Capacitor project establishes these build requirements:

- JDK 21 (generated Capacitor compile source/target compatibility);
- Gradle wrapper 8.14.3;
- Android Gradle Plugin 8.13.0;
- Android SDK platform 36;
- Android SDK Build Tools 35.0.0;
- Android SDK Platform-Tools;
- minimum SDK 24 and target SDK 36.

To install the Windows IDE/JDK host pieces explicitly:

```powershell
.\bootstrap\windows.ps1 -WithAndroid
```

Android Studio's supported first-launch SDK Manager remains a clear checkpoint:
install Platform 36, Build Tools 35.0.0, and Platform-Tools, then rerun. The
bootstrap checks them and creates `frontend/android/local.properties` only when
that ignored non-secret file is absent. An existing file is preserved; a stale
`sdk.dir` produces an actionable error.

`make doctor` reports Android as optional. `scripts/doctor.sh --android` makes
the Linux-side JDK/SDK checks required. Native server provisioning skips
Android.

When WSL has no Linux Chrome binary, the repository includes a Karma launcher
that gives Windows Edge a Windows-native temporary profile path:

```bash
cd frontend
CHROME_BIN=/mnt/c/PROGRA~2/Microsoft/Edge/Application/msedge.exe \
  npm test -- --watch=false --browsers=WSLEdgeHeadless
```

The launcher derives `%TEMP%` through WSL interop and creates a unique temporary
profile per Karma process; it does not encode a drive letter or username in
application logic.

## What may remain on the Windows system drive

It is normal for Windows, WSL runtime/kernel components, the Windows NVIDIA
driver, Windows Terminal, Git for Windows, VS Code, Android Studio, and other
ordinary host applications to remain on `C:`. No F.A.N. package version relies
on undocumented C: state.

Large mutable data should live outside C: when practical:

- the WSL VHD can use the bootstrap data root on another drive;
- the checkout lives inside that VHD at `~/Development/FAN`;
- model and tool caches use configurable XDG/F.A.N. cache roots;
- model weights are recoverable and never committed.

## Legacy ambiguity

Top-level `Pipfile`, `Pipfile.lock`, `API`, `LLM`, `WEB`, `outdated`,
`scripts/manage.sh`, and `start/*.cmd` belong to earlier prototypes. Some contain
old `~/FAN`, queue-worker, or host-path assumptions. They are not provisioning
or dependency sources of truth and were intentionally not deleted in this
initiative. Cleanup should be a separate evidence-based task.

## Upstream mechanisms

The implementation follows the supported mechanisms documented by the relevant
vendors:

- [Microsoft WSL installation and commands](https://learn.microsoft.com/windows/wsl/install)
- [Microsoft systemd support in WSL](https://learn.microsoft.com/windows/wsl/systemd)
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Desktop WSL integration](https://docs.docker.com/desktop/features/wsl/)
- [uv project synchronization](https://docs.astral.sh/uv/concepts/projects/sync/)
- [NVIDIA CUDA on WSL guidance](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
- [Android Gradle Plugin 8.13 compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes)

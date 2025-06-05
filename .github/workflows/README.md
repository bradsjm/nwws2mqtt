# GitHub Actions Docker Workflows

This directory contains GitHub Actions workflows for building, testing, and publishing Docker containers for the NWWS2MQTT project.

## Workflows Overview

### 1. Manual Docker Build (`docker-publish.yml`)

**Trigger**: Manual dispatch via GitHub Actions UI

**Purpose**: On-demand building and publishing of Docker images with full control over build parameters.

**Features**:
- ✅ Manual trigger with customizable inputs
- ✅ Multi-platform builds (AMD64, ARM64)
- ✅ Configurable image tags
- ✅ Optional registry push
- ✅ Security vulnerability scanning with Trivy
- ✅ Comprehensive build summaries
- ✅ Image testing and validation
- ✅ SBOM and provenance generation

**Usage**:
1. Go to **Actions** tab in GitHub
2. Select **Build and Publish Docker Image**
3. Click **Run workflow**
4. Configure parameters:
   - **Tag**: Custom tag for the image (default: `latest`)
   - **Push to registry**: Whether to push to GitHub Container Registry
   - **Platforms**: Target architectures (default: `linux/amd64,linux/arm64`)

### 2. Automated Docker CI/CD (`docker-ci.yml`)

**Triggers**:
- 📦 **Releases**: Automatically builds when a new release is published
- 🔄 **Pull Requests**: Builds and tests on PRs affecting Docker-related files

**Features**:
- ✅ Automatic semantic versioning for releases
- ✅ PR validation with Docker builds
- ✅ Security scanning on all builds
- ✅ Multi-platform support
- ✅ Intelligent caching for faster builds
- ✅ PR comments with build results
- ✅ Automatic cleanup of PR artifacts

### 3. Development Workflow (`docker-dev.yml`)

**Trigger**: Manual dispatch for development testing

**Purpose**: Comprehensive testing and validation of Docker images during development.

**Features**:
- ✅ Multiple test types (build, test, integration, full)
- ✅ Configurable Python versions
- ✅ Integration testing with Docker Compose
- ✅ Performance and resource monitoring
- ✅ Security scanning with detailed reports
- ✅ Automatic cleanup options
- ✅ Local development guidance

**Test Types**:
- **Build**: Basic image building and validation
- **Test**: Functionality and dependency testing
- **Integration**: Full stack testing with MQTT broker
- **Full**: Complete test suite including performance and security

**Release Workflow**:
When you publish a release (e.g., `v1.2.3`), the workflow automatically:
1. Builds Docker images for multiple platforms
2. Tags with semantic versions (`1.2.3`, `1.2`, `1`, `latest`)
3. Pushes to GitHub Container Registry
4. Runs security scans
5. Generates deployment documentation

## Docker Image Details

### Base Configuration
- **Base Image**: `python:3.13-slim-bookworm`
- **Architecture**: Multi-platform (AMD64, ARM64)
- **Security**: Non-root user execution
- **Size**: Optimized multi-stage build

### Available Tags

| Tag Pattern | Description | Example |
|-------------|-------------|---------|
| `latest` | Latest stable release | `ghcr.io/owner/nwws2mqtt:latest` |
| `v{version}` | Specific version | `ghcr.io/owner/nwws2mqtt:v1.2.3` |
| `v{major}.{minor}` | Minor version | `ghcr.io/owner/nwws2mqtt:v1.2` |
| `v{major}` | Major version | `ghcr.io/owner/nwws2mqtt:v1` |
| `{branch}-{sha}` | Branch builds | `ghcr.io/owner/nwws2mqtt:main-abc1234` |
| `pr-{number}` | PR builds | `ghcr.io/owner/nwws2mqtt:pr-42` |

### Registry Information
- **Registry**: GitHub Container Registry (`ghcr.io`)
- **Repository**: `ghcr.io/{owner}/nwws2mqtt`
- **Visibility**: Public (configurable)

## Security Features

### Vulnerability Scanning
- **Scanner**: Trivy (industry-standard)
- **Frequency**: Every build
- **Integration**: Results uploaded to GitHub Security tab
- **Coverage**: OS packages, Python dependencies, and configuration issues

### Build Security
- **Provenance**: SLSA attestations for supply chain security  
- **SBOM**: Software Bill of Materials generation
- **Minimal Base**: Slim images with only necessary dependencies
- **User Security**: Non-root container execution

## Usage Examples

### Pull and Run Latest Image
```bash
# Pull the latest stable release
docker pull ghcr.io/{owner}/nwws2mqtt:latest

# Run with basic configuration
docker run -d --name nwws2mqtt \
  -p 8080:8080 \
  -e MQTT_BROKER_HOST=mqtt.local \
  -e NWWS_USERNAME=your_username \
  -e NWWS_PASSWORD=your_password \
  ghcr.io/{owner}/nwws2mqtt:latest
```

### Development Workflow
```bash
# For testing specific PR changes
docker pull ghcr.io/{owner}/nwws2mqtt:pr-123

# For testing specific commits
docker pull ghcr.io/{owner}/nwws2mqtt:main-abc1234
```

### Production Deployment
```bash
# Use specific version for production stability
docker pull ghcr.io/{owner}/nwws2mqtt:v1.2.3

# Or use major version for automatic minor updates
docker pull ghcr.io/{owner}/nwws2mqtt:v1
```

## Monitoring and Observability

### Build Monitoring
- **Build Status**: Available in Actions tab
- **Build History**: Complete build logs and artifacts
- **Performance**: Build time and cache hit rate tracking

### Security Monitoring
- **Vulnerability Alerts**: Automatic GitHub security alerts
- **Dependency Updates**: Dependabot integration (if configured)
- **Security Tab**: Centralized security findings

### Image Metrics
- **Size Tracking**: Build summaries include image size
- **Layer Analysis**: Layer count and composition
- **Performance**: Multi-platform build times

## Maintenance

### Regular Tasks
1. **Review Security Scans**: Check Security tab weekly
2. **Update Base Images**: Monitor Python upstream releases
3. **Clean Old Images**: GitHub automatically manages retention
4. **Monitor Build Performance**: Review cache hit rates

### Troubleshooting

#### Build Failures
- Check Actions logs for specific error messages
- Verify Dockerfile syntax and dependencies
- Review platform-specific build issues

#### Registry Issues
- Ensure `GITHUB_TOKEN` has package write permissions
- Check repository package settings
- Verify registry authentication

#### Security Scan Failures
- Review Trivy scan results in Security tab
- Update dependencies to address vulnerabilities
- Consider base image updates

## Configuration

### Required Secrets
- `GITHUB_TOKEN`: Automatically provided (no setup needed)

### Optional Configuration
- **Package Visibility**: Configure in repository settings
- **Retention Policy**: Adjust in package settings
- **Branch Protection**: Configure required status checks

### Environment Variables
The workflows use these environment variables:
- `REGISTRY`: Container registry URL (`ghcr.io`)
- `IMAGE_NAME`: Repository name (auto-detected)

## Contributing

When modifying these workflows:

1. **Test Changes**: Use manual workflow dispatch to test modifications
2. **Security Review**: Ensure no secrets are exposed in logs
3. **Documentation**: Update this README for significant changes
4. **Validation**: Test with actual PR to verify PR workflow

### Workflow Modification Guidelines
- Always use specific action versions (not `@main`)
- Include proper error handling and cleanup
- Maintain backward compatibility where possible
- Add appropriate permissions and security controls
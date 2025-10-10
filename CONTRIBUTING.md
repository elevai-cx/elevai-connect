# Contributing to elevai-connect

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Project Structure

Understanding the project structure is crucial for effective contributions:

```
elevai-connect/
├── core/                         # Core infrastructure 
├── custom/                       # User customizations (typically not merged)
├── config/                       # Configuration management
├── lambda-code/                  # Function code
└── __main__.py                   # Entry point
└── Pulumi.dev.yaml.example       # Template pulumi stack file
```

## Types of Contributions

### 1. Core Infrastructure Improvements

Contributions to the `core/` directory that benefit all users:

- Bug fixes in core modules
- New core resources
- Performance improvements
- Security enhancements
- Documentation improvements

**Process:**
1. Fork the repository
2. Create a feature branch from `main`
3. Make changes
4. Test thoroughly in a dev stack
5. Submit a pull request


### 2. Documentation

Documentation improvements help everyone:

- Fixing typos or unclear instructions
- Adding examples
- Improving troubleshooting guides
- Adding architecture diagrams
- Clarifying configuration options

## Development Guidelines

### Code Style

Follow PEP 8 style guidelines for Python code:

```bash
# Install development dependencies
pip install black flake8 mypy

# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

### Resource Naming

Use consistent naming conventions:

```python
# Good
contacts_table = aws.dynamodb.Table(
    "contacts-table",
    name=pulumi.Output.concat(project, "-", stack, "-contacts"),
    ...
)

# Bad
table1 = aws.dynamodb.Table("tbl", ...)
```

### Documentation

All functions should have docstrings:

```python
def create_resource(tags: Dict[str, str]) -> aws.Resource:
    """
    Create a specific AWS resource.
    
    Args:
        tags: Tags to apply to the resource
        
    Returns:
        The created resource
    """
    pass
```

### Security

- Never commit secrets or credentials
- Use AWS Secrets Manager / Parameter Store (secureString) for sensitive data
- Follow least-privilege IAM principles
- Enable encryption by default
- Document security considerations

**Required Security Compliance Checks:**

All contributions must maintain compliance with:
- ✅ CIS AWS Foundations Benchmark v1.2.0
- ✅ PCI DSS v4.0.1
- ✅ AWS Foundational Security Best Practices v1.0.0
- ✅ AWS Resource Tagging Standard v1.0.0

Before submitting a PR, verify your changes:
- Do not introduce security vulnerabilities
- Maintain encryption for data at rest and in transit
- Follow established IAM patterns
- Include appropriate security group rules
- Add required tags to all resources

See [SECURITY.md](SECURITY.md) for full details.

## Testing

### Before Submitting

1. **Preview Changes**
   ```bash
   pulumi preview
   ```

2. **Deploy to Dev Stack**
   ```bash
   pulumi stack init test-contribution
   pulumi up
   ```

3. **Verify in AWS Console**
   - Check resources are created correctly
   - Verify tags are applied
   - Test functionality

4. **Clean Up**
   ```bash
   pulumi destroy
   pulumi stack rm test-contribution
   ```

### Test Checklist

- [ ] Code follows style guidelines
- [ ] All functions have docstrings
- [ ] Changes don't break existing functionality
- [ ] Resources are properly tagged
- [ ] Configuration is documented
- [ ] README is updated if needed
- [ ] Tested in a clean stack
- [ ] No hardcoded values
- [ ] IAM roles follow least privilege
- [ ] **Security compliance verified** (see Security section below)

## Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Keep changes focused and atomic
- Write clear commit messages
- Reference issues if applicable
- Ensure user inputs are added to Pulumi.dev.yaml.example

### 3. Update Documentation

- Update README if needed
- Add comments to complex code
- Update CHANGELOG if significant

### 4. Submit Pull Request

**PR Title Format:**
- `feat: Add new feature`
- `fix: Fix bug in module`
- `docs: Update documentation`
- `refactor: Improve code structure`

**PR Description Should Include:**
- What changes were made
- Why the changes are needed
- How to test the changes
- Screenshots if applicable
- Breaking changes (if any)

**Example PR Description:**
```markdown
## Changes
- Added support for Amazon Connect queues
- Created new module: core/queues.py
- Updated documentation

## Motivation
Many users need to create queues programmatically

## Testing
1. Deploy with `pulumi up`
2. Verify queue in Connect console
3. Test queue functionality

## Breaking Changes
None
```

### 5. Code Review

- Address reviewer feedback promptly
- Keep discussions focused and respectful
- Be open to suggestions

## Branch Strategy

- `main`: Stable, production-ready code
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

## Commit Message Guidelines

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(connect): Add support for contact flows

Implements contact flow creation with JSON configuration
support. Includes validation and error handling.

Closes #123
```

```
fix(lambda): Correct IAM policy for DynamoDB access

The Lambda function was unable to write to DynamoDB due to
missing permissions. Added PutItem action to policy.
```

## What NOT to Contribute

Please **do not** submit PRs for:

- Changes to `custom/` directory (this is for user customizations)
- Hardcoded credentials or secrets
- Breaking changes without discussion
- Large refactors without prior agreement
- Incomplete features
- Untested code

## Getting Help

- Open an issue for bugs or feature requests
- Discuss major changes before implementing
- Ask questions in issues or discussions
- Check existing PRs for similar work

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the project
- Show empathy towards others

### Unacceptable Behaviour

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0, the same license as the project.

## Questions?

Feel free to:
- Open an issue for questions
- Reach out to maintainers
- Check existing documentation

Thank you for contributing! 🎉

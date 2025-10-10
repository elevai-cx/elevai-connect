# elevai-connect Workshops

This directory contains hands-on workshops for learning and implementing features of the elevai-connect Amazon Connect infrastructure.

## Available Workshops

### 1. Amazon Q Knowledge Base Setup
**Path:** `q-knowledgebase-set-up/`  
**Duration:** 30-45 minutes  
**Difficulty:** Beginner  

**What you'll learn:**
- Upload documents to Amazon Q Knowledge Base
- Configure document metadata and tagging
- Create and configure Lex bots for FAQ handling
- Import and publish Amazon Connect contact flows
- Test Q integration in Connect chat

**Prerequisites:**
- Amazon Connect instance deployed via elevai-connect
- AWS Console access
- Pulumi CLI configured

**Start here:** [q-knowledgebase-set-up/README.md](q-knowledgebase-set-up/README.md)

---

## How to Use These Workshops

1. **Ensure prerequisites are met** - Check each workshop's requirements
2. **Read through the entire workshop first** - Understand all steps before starting
3. **Follow along step-by-step** - Don't skip steps
4. **Use Claude Code for assistance** - Ask questions about any step
5. **Verify outputs** - Use provided troubleshooting tips if needed

## Workshop Structure

Each workshop contains:
- `README.md` - Main workshop instructions
- Sample files and resources needed for the workshop
- Troubleshooting guidance
- Links to further reading

## Getting Help

If you encounter issues:
1. Check the Troubleshooting section in the workshop README
2. Review the main project documentation in `/CLAUDE.md`
3. Ask Claude Code for assistance with specific steps
4. Verify your Pulumi stack configuration

## Contributing Workshops

When adding new workshops:
1. Create a new directory under `workshops/`
2. Include a comprehensive `README.md`
3. Add all required sample files and resources
4. Update this index file with the new workshop
5. Test the workshop end-to-end before committing
#!/usr/bin/env python3
"""
Platform-Agnostic Render Pipeline
Converts src/ (generic) to dist/{provider}/ (provider-specific)
"""

import os
import sys
import yaml
import json
import re
from pathlib import Path
from typing import Dict, Any

class ModelResolver:
    """Resolves canonical model names to provider-specific names"""

    def __init__(self, models_yaml: str):
        with open(models_yaml) as f:
            self.config = yaml.safe_load(f)
        self.role_models = self.config.get('role_models', {})
        self.provider_features = self.config.get('provider_features', {})

    def get_model(self, role: str, provider: str) -> str:
        """Get provider-specific model name for a role"""
        if role not in self.role_models:
            return f"UNKNOWN_ROLE_{role}"

        role_config = self.role_models[role]
        if provider not in role_config.get('providers', {}):
            return role_config['canonical']  # Fallback to canonical

        return role_config['providers'][provider]

    def get_effort(self, role: str) -> str:
        """Get effort level for a role"""
        return self.role_models.get(role, {}).get('effort', 'unknown')

    def get_thinking_support(self, provider: str) -> bool:
        """Check if provider supports thinking mode"""
        return self.provider_features.get(provider, {}).get('thinking', False)

    def get_deltas(self, role: str, provider: str) -> list:
        """Get capability deltas for this role on this provider"""
        deltas = []
        role_config = self.role_models.get(role, {})
        provider_config = self.provider_features.get(provider, {})

        # Check thinking support
        if role_config.get('thinking') and not provider_config.get('thinking'):
            deltas.append("⚠️ This role uses extended thinking, but provider doesn't support it - using fallback reasoning")

        # Check structured output
        if not provider_config.get('structured_output', True):
            deltas.append("⚠️ Provider doesn't guarantee structured outputs - may need JSON parsing")

        # Check max tokens
        max_tokens = provider_config.get('max_tokens', 4096)
        if max_tokens < 8000:
            deltas.append(f"⚠️ Provider has limited context ({max_tokens} tokens) - may affect complex tasks")

        return deltas

class RenderPipeline:
    """Renders src/ content to provider-specific output"""

    def __init__(self, src_dir: str, dist_dir: str, provider: str, models_yaml: str):
        self.src_dir = Path(src_dir)
        self.dist_dir = Path(dist_dir)
        self.provider = provider
        self.resolver = ModelResolver(models_yaml)

    def render_file(self, src_file: Path, dest_file: Path) -> None:
        """Render a single file, substituting provider-specific values"""

        with open(src_file) as f:
            content = f.read()

        # Extract role name from file path or content
        role_name = src_file.stem  # e.g., "engineer-agent" -> "engineer"
        role_key = role_name.replace('-agent', '').replace('-', '_')

        # Get provider-specific model
        model = self.resolver.get_model(role_key, self.provider)
        effort = self.resolver.get_effort(role_key)

        # Substitute generic terms with provider-specific ones
        substitutions = {
            'claude-haiku': model if 'haiku' in role_key else self.resolver.get_model('engineer', self.provider),
            'claude-sonnet': model if 'sonnet' in role_key else self.resolver.get_model('senior_engineer', self.provider),
            'claude-opus': model if 'opus' in role_key else self.resolver.get_model('security_engineer', self.provider),
            '{{MODEL}}': model,
            '{{PROVIDER}}': self.provider,
            '{{EFFORT}}': effort,
        }

        # Perform substitutions
        for generic, specific in substitutions.items():
            content = content.replace(generic, specific)

        # Add delta warnings if applicable
        deltas = self.resolver.get_deltas(role_key, self.provider)
        if deltas:
            delta_header = f"\n\n## Platform Deltas ({self.provider})\n\n"
            for delta in deltas:
                delta_header += f"- {delta}\n"
            content = content + delta_header

        # Ensure destination directory exists
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        # Write rendered file
        with open(dest_file, 'w') as f:
            f.write(content)

        print(f"✅ Rendered: {src_file.name} → {self.provider}")

    def render_all(self) -> None:
        """Render all src files to provider-specific dist output"""

        roles_dir = self.src_dir / 'roles'
        dest_roles_dir = self.dist_dir / 'roles'

        if not roles_dir.exists():
            print(f"⚠️ No roles directory found in {self.src_dir}")
            return

        for src_file in roles_dir.glob('*.md'):
            dest_file = dest_roles_dir / src_file.name
            self.render_file(src_file, dest_file)

        # Copy models.json to dist
        self.copy_models_manifest()

    def copy_models_manifest(self) -> None:
        """Create models.json in dist showing what was rendered"""
        manifest = {
            'provider': self.provider,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'role_models': {}
        }

        for role, config in self.resolver.role_models.items():
            manifest['role_models'][role] = {
                'model': self.resolver.get_model(role, self.provider),
                'effort': config.get('effort'),
                'thinking': config.get('thinking'),
                'canonical': config.get('canonical'),
            }

        manifest_file = self.dist_dir / 'models.json'
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"✅ Created manifest: {manifest_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python render/main.py <provider> [src_dir] [dist_dir]")
        print("  Supported providers: copilot, claude, openai, google, meta")
        sys.exit(1)

    provider = sys.argv[1]
    src_dir = sys.argv[2] if len(sys.argv) > 2 else 'src'
    dist_dir = sys.argv[3] if len(sys.argv) > 3 else f'dist/{provider}'

    # Get project root (one level up from render/main.py)
    script_dir = Path(__file__).parent.parent
    models_yaml = script_dir / 'models.yaml'
    src_path = script_dir / src_dir
    dist_path = script_dir / dist_dir

    print(f"\n🎨 Rendering {src_path} → {dist_path} for {provider}")
    print(f"📚 Using models from {models_yaml}\n")

    pipeline = RenderPipeline(str(src_path), str(dist_path), provider, str(models_yaml))
    pipeline.render_all()

    print(f"\n✅ Rendering complete for {provider}!")
    print(f"📁 Output: {dist_path}/\n")

if __name__ == '__main__':
    main()

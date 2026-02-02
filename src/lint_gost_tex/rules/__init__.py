from __future__ import annotations

from .abbrev import AbbreviationRule
from .base import Rule
from .captions import CaptionPunctuationRule
from .images import ImageWidthRule
from .illustrations import IllustrationOrderRule
from .lists import CustomListRule, ListItemCaseRule, ListItemPunctuationRule, NestedListRule
from .refs import LinkPunctuationRule, RefSpacingRule
from .spelling import SpellcheckRule
from .styles import TextStyleRule
from .unicode_chars import UnicodeCharRule
from ..config import Config


def build_rules(config: Config) -> list[Rule]:
    return [
        ImageWidthRule(config.images.required_width),
        RefSpacingRule(config.refs.commands),
        LinkPunctuationRule(config.links.commands),
        TextStyleRule(config.styles.commands),
        CustomListRule(
            allowed_envs=config.lists.allowed_envs,
            list_envs=config.lists.list_envs,
            disallow_begin_optional=config.lists.disallow_begin_optional,
            disallow_item_optional=config.lists.disallow_item_optional,
        ),
        NestedListRule(config.lists.list_envs),
        ListItemPunctuationRule(
            list_envs=config.lists.list_envs,
            skip_commands=config.list_items.skip_commands,
            two_arg_commands=config.list_items.two_arg_commands,
            sentence_endings=config.list_items.sentence_endings,
            last_end=config.list_items.last_end,
            non_last_end=config.list_items.non_last_end,
        ),
        ListItemCaseRule(
            list_envs=config.lists.list_envs,
            skip_commands=config.list_items.skip_commands,
            two_arg_commands=config.list_items.two_arg_commands,
        ),
        CaptionPunctuationRule(config.captions.commands, config.captions.forbid_trailing),
        SpellcheckRule(
            custom_dict=config.spellcheck.custom_dict,
            extra_ru_dicts=config.spellcheck.extra_ru_dicts,
            extra_en_dicts=config.spellcheck.extra_en_dicts,
            ignore_envs=config.spellcheck.ignore_envs,
            skip_commands=config.spellcheck.skip_commands,
            keep_commands=config.spellcheck.keep_commands,
            min_word_length=config.spellcheck.min_word_length,
            ignore_uppercase_acronyms=config.spellcheck.ignore_uppercase_acronyms,
        ),
        IllustrationOrderRule(config.illustrations.envs, config.illustrations.ref_commands),
        AbbreviationRule(
            banned_words=config.abbrev.banned_words,
            banned_patterns=config.abbrev.banned_patterns,
            allow_words=config.abbrev.allow_words,
            skip_commands=config.abbrev.skip_commands,
            two_arg_commands=config.abbrev.two_arg_commands,
        ),
        UnicodeCharRule(config.unicode.allowed_extra),
    ]

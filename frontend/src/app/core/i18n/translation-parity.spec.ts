type TranslationTree = Record<string, unknown>;

const INTERPOLATION_PATTERN = /{{\s*([^{}\s]+)\s*}}/g;

async function loadTranslation(
  language: string,
): Promise<TranslationTree> {
  const response = await fetch(
    `assets/i18n/${language}.json`,
  );

  if (!response.ok) {
    throw new Error(
      `Could not load ${language} translations.`,
    );
  }

  return response.json() as Promise<TranslationTree>;
}

function leafPaths(
  value: unknown,
  parentPath = '',
): string[] {
  if (!isTranslationTree(value)) {
    return [parentPath];
  }

  const paths: string[] = [];

  for (const [key, child] of Object.entries(value)) {
    paths.push(...leafPaths(
      child,
      parentPath === ''
        ? key
        : `${parentPath}.${key}`,
    ));
  }

  return paths;
}

function valueAtPath(
  translations: TranslationTree,
  path: string,
): unknown {
  return path.split('.').reduce<unknown>(
    (value, segment) => {
      if (!isTranslationTree(value)) {
        return undefined;
      }

      return value[segment];
    },
    translations,
  );
}

function interpolationParameters(value: unknown): string[] {
  if (typeof value !== 'string') {
    return [];
  }

  const parameters: string[] = [];
  INTERPOLATION_PATTERN.lastIndex = 0;

  let match = INTERPOLATION_PATTERN.exec(value);

  while (match !== null) {
    parameters.push(match[1]);
    match = INTERPOLATION_PATTERN.exec(value);
  }

  return parameters.sort();
}

function isTranslationTree(
  value: unknown,
): value is TranslationTree {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value)
  );
}

describe('translation assets', () => {
  let english: TranslationTree;
  let russian: TranslationTree;

  beforeAll(async () => {
    [english, russian] = await Promise.all([
      loadTranslation('en'),
      loadTranslation('ru'),
    ]);
  });

  it('keeps English and Russian deep translation keys in parity', () => {
    expect(leafPaths(russian).sort()).toEqual(
      leafPaths(english).sort(),
    );
  });

  it('keeps interpolation placeholders in parity', () => {
    for (const path of leafPaths(english)) {
      expect(
        interpolationParameters(
          valueAtPath(russian, path),
        ),
      )
        .withContext(path)
        .toEqual(
          interpolationParameters(
            valueAtPath(english, path),
          ),
        );
    }
  });
});

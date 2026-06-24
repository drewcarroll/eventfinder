import 'package:flutter/material.dart';

/// The app's visual identity — a single source of truth for colours,
/// gradients, radii and the assembled light/dark [ThemeData].
///
/// The palette is a blue + pink duo (researched from the widely-used Tailwind
/// scale: blue-500 / pink-500) on a soft blue canvas with white cards. Flat,
/// solid fills do the heavy lifting; the only gradient left is a small accent
/// on the loading screen.
class AppColors {
  AppColors._();

  // Brand duo.
  static const Color blue = Color(0xFF3B82F6); // Tailwind blue-500
  static const Color blueDeep = Color(0xFF2563EB); // blue-600
  static const Color blueLight = Color(0xFF93C5FD); // blue-300
  static const Color pink = Color(0xFFEC4899); // pink-500
  static const Color pinkSoft = Color(0xFFF9A8D4); // pink-300

  // Semantic swipe colours.
  static const Color like = Color(0xFF22C58B);
  static const Color pass = Color(0xFFFB5C74);

  // Light neutrals — a gentle blue-pink canvas with white surfaces.
  static const Color lightBg = Color(0xFFEEF1FB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceAlt = Color(0xFFE7ECFB);
  static const Color ink = Color(0xFF182038);
  static const Color inkSoft = Color(0xFF6A7191);

  // Dark neutrals.
  static const Color darkBg = Color(0xFF0E1220);
  static const Color darkSurface = Color(0xFF181D2E);
  static const Color darkSurfaceAlt = Color(0xFF232A40);
}

/// Reusable gradients. [brand] is a blue→pink accent used sparingly (the
/// loading screen); [scrim] darkens the bottom of card imagery so text stays
/// legible.
class AppGradients {
  AppGradients._();

  static const LinearGradient brand = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [AppColors.blue, AppColors.pink],
  );

  static const LinearGradient scrim = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0x00000000), Color(0x99000000)],
    stops: [0.45, 1.0],
  );
}

/// Corner radii used across the app, kept consistent so surfaces feel related.
class AppRadii {
  AppRadii._();

  static const double sm = 14;
  static const double md = 20;
  static const double lg = 28;
  static const double pill = 999;
}

class AppTheme {
  AppTheme._();

  static const String fontFamily = 'Poppins';

  static ThemeData get light => _build(Brightness.light);
  static ThemeData get dark => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isLight = brightness == Brightness.light;

    final scheme =
        ColorScheme.fromSeed(
          seedColor: AppColors.blue,
          brightness: brightness,
        ).copyWith(
          primary: isLight ? AppColors.blue : AppColors.blueLight,
          secondary: AppColors.pink,
          tertiary: AppColors.pinkSoft,
          surface: isLight ? AppColors.lightSurface : AppColors.darkSurface,
          surfaceContainerHighest:
              isLight ? AppColors.lightSurfaceAlt : AppColors.darkSurfaceAlt,
          onSurface: isLight ? AppColors.ink : const Color(0xFFE8EBF7),
          onSurfaceVariant:
              isLight ? AppColors.inkSoft : const Color(0xFF9CA3C0),
        );

    final bg = isLight ? AppColors.lightBg : AppColors.darkBg;
    final base = ThemeData(brightness: brightness, useMaterial3: true);
    final text = _textTheme(base.textTheme, scheme.onSurface);

    return base.copyWith(
      colorScheme: scheme,
      scaffoldBackgroundColor: bg,
      canvasColor: bg,
      textTheme: text,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: AppBarTheme(
        backgroundColor: bg,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: text.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shadowColor: AppColors.blue.withValues(alpha: 0.16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isLight ? Colors.white : AppColors.darkSurfaceAlt,
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        hintStyle: text.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
        labelStyle: text.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
        prefixIconColor: scheme.onSurfaceVariant,
        border: _inputBorder(scheme.outlineVariant),
        enabledBorder: _inputBorder(
          isLight ? const Color(0xFFDCE3F5) : Colors.white12,
        ),
        focusedBorder: _inputBorder(scheme.primary, width: 1.8),
        errorBorder: _inputBorder(scheme.error),
        focusedErrorBorder: _inputBorder(scheme.error, width: 1.8),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(0, 54),
          padding: const EdgeInsets.symmetric(horizontal: 24),
          textStyle: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 52),
          foregroundColor: scheme.onSurface,
          side: BorderSide(
            color: isLight ? const Color(0xFFD7DEF2) : Colors.white24,
          ),
          textStyle: text.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: scheme.primary,
          textStyle: text.titleMedium?.copyWith(fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: scheme.surfaceContainerHighest,
        selectedColor: scheme.primary,
        side: BorderSide.none,
        showCheckmark: false,
        labelStyle: text.labelLarge?.copyWith(color: scheme.onSurface),
        secondaryLabelStyle:
            text.labelLarge?.copyWith(color: scheme.onPrimary),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.pill),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: isLight ? Colors.white : AppColors.darkSurface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 68,
        indicatorColor: scheme.primary.withValues(alpha: 0.14),
        labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => text.labelMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: states.contains(WidgetState.selected)
                ? scheme.primary
                : scheme.onSurfaceVariant,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? scheme.primary
                : scheme.onSurfaceVariant,
          ),
        ),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: scheme.primary,
        inactiveTrackColor: scheme.primary.withValues(alpha: 0.16),
        thumbColor: scheme.primary,
        overlayColor: scheme.primary.withValues(alpha: 0.16),
        trackHeight: 5,
        valueIndicatorColor: scheme.primary,
        valueIndicatorTextStyle: text.labelMedium?.copyWith(
          color: scheme.onPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: isLight ? AppColors.ink : AppColors.darkSurfaceAlt,
        contentTextStyle: text.bodyMedium?.copyWith(color: Colors.white),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
        insetPadding: const EdgeInsets.all(16),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        modalBarrierColor: Colors.black.withValues(alpha: 0.45),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadii.lg),
          ),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: isLight ? const Color(0xFFDFE5F4) : Colors.white12,
        thickness: 1,
        space: 1,
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: scheme.primary,
      ),
      listTileTheme: const ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(AppRadii.sm)),
        ),
      ),
    );
  }

  static OutlineInputBorder _inputBorder(Color color, {double width = 1.2}) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadii.md),
      borderSide: BorderSide(color: color, width: width),
    );
  }

  static TextTheme _textTheme(TextTheme base, Color onSurface) {
    final poppins = base.apply(
      fontFamily: fontFamily,
      bodyColor: onSurface,
      displayColor: onSurface,
    );

    TextStyle? tune(
      TextStyle? style, {
      double? spacing,
      FontWeight? weight,
      double? height,
    }) {
      return style?.copyWith(
        letterSpacing: spacing,
        fontWeight: weight,
        height: height,
      );
    }

    return poppins.copyWith(
      displaySmall:
          tune(poppins.displaySmall, spacing: -1, weight: FontWeight.w800),
      headlineLarge:
          tune(poppins.headlineLarge, spacing: -0.8, weight: FontWeight.w800),
      headlineMedium:
          tune(poppins.headlineMedium, spacing: -0.6, weight: FontWeight.w700),
      headlineSmall:
          tune(poppins.headlineSmall, spacing: -0.4, weight: FontWeight.w700),
      titleLarge:
          tune(poppins.titleLarge, spacing: -0.3, weight: FontWeight.w700),
      titleMedium:
          tune(poppins.titleMedium, spacing: -0.1, weight: FontWeight.w600),
      bodyLarge: tune(poppins.bodyLarge, height: 1.45),
      bodyMedium: tune(poppins.bodyMedium, height: 1.45),
      labelLarge:
          tune(poppins.labelLarge, spacing: 0.1, weight: FontWeight.w600),
    );
  }
}

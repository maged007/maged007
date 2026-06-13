import 'package:flutter/material.dart';

/// عنصر قائمة منسدلة مع عنوان عربي، قابل لإعادة الاستخدام.
class LabeledDropdown<T> extends StatelessWidget {
  final String label;
  final T? value;
  final List<T> items;
  final String Function(T) itemLabel;
  final ValueChanged<T?> onChanged;
  final bool enabled;

  const LabeledDropdown({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.itemLabel,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6, right: 4),
          child: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          ),
        ),
        DropdownButtonFormField<T>(
          value: value,
          isExpanded: true,
          items: items
              .map((e) => DropdownMenuItem<T>(
                    value: e,
                    child: Text(itemLabel(e)),
                  ))
              .toList(),
          onChanged: enabled ? onChanged : null,
          hint: const Text('اختر...'),
        ),
        const SizedBox(height: 16),
      ],
    );
  }
}
